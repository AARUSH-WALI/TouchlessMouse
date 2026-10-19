"""Touchless Computer Control System - Rule-Based Gesture Detection Engine."""

import time
import math
from typing import List, Optional, Tuple, Dict, Any
from src.utils.geometry import euclidean_distance, Point
from src.core.hand_tracker import (
    WRIST, THUMB_TIP, INDEX_TIP, MIDDLE_TIP, RING_TIP, PINKY_TIP,
    INDEX_MCP, MIDDLE_MCP, RING_MCP, PINKY_MCP,
    INDEX_PIP, MIDDLE_PIP, RING_PIP, PINKY_PIP
)


class GestureEngine:
    """
    Robust rule-based gesture detection with hysteresis, proximity calculation,
    horizontal swipe detection (next/prev page), L-shape zoom in/out,
    natural peace-sign scrolling, and debounce cooldowns.
    """

    def __init__(self, config: Optional[Any] = None):
        cfg = config or {}
        g_cfg = cfg.get("gestures", {}) if hasattr(cfg, "get") else {}

        # Raw distance thresholds (in camera space ~0.0 to 1.0)
        self.pinch_on = float(g_cfg.get("pinch_on_threshold", 0.055))
        self.pinch_off = float(g_cfg.get("pinch_off_threshold", 0.080))

        # Hand-scale normalized thresholds (optional backup)
        self.pinch_norm_on = float(g_cfg.get("pinch_norm_on", 0.18))
        self.pinch_norm_off = float(g_cfg.get("pinch_norm_off", 0.25))

        self.click_cooldown_ms = float(g_cfg.get("click_cooldown_ms", 250))
        self.required_frames = int(g_cfg.get("consecutive_frames_required", 2))
        self.drag_hold_frames = int(g_cfg.get("drag_hold_frames", 8))
        self.scroll_sensitivity = float(g_cfg.get("scroll_sensitivity", 5))

        # Internal state
        self.is_index_pinching = False
        self.is_middle_pinching = False
        self.pinch_counter = 0
        self.last_click_time = 0.0
        self.candidate_gesture = None
        self.consecutive_count = 0
        self.current_stable_gesture = "idle"
        self.prev_scroll_y = None

        # Swipe & Motion tracking
        self.wrist_history = []  # List of (timestamp, x, y)
        self.last_swipe_time = 0.0
        self.swipe_cooldown_ms = 450.0

        # Zoom tracking
        self.prev_zoom_y = None
        self.last_zoom_time = 0.0
        self.zoom_cooldown_ms = 220.0

        # Open palm hold tracking (prevents accidental pause when hand enters frame)
        self.open_palm_start_time = None
        self.open_palm_hold_duration_sec = 0.85

    def get_hand_size(self, landmarks) -> float:
        """Reference scale distance from WRIST (0) to MIDDLE_FINGER_MCP (9)."""
        wrist = landmarks[WRIST]
        middle_mcp = landmarks[MIDDLE_MCP]
        size = euclidean_distance(wrist, middle_mcp)
        return size if size > 1e-6 else 1.0

    def normalized_distance(self, landmarks, idx_a: int, idx_b: int) -> float:
        """Euclidean distance between two landmarks divided by hand size."""
        raw = euclidean_distance(landmarks[idx_a], landmarks[idx_b])
        return raw / self.get_hand_size(landmarks)

    def calculate_proximity(self, dist: float, on_thresh: float, max_range: float = 0.16) -> float:
        """Calculates 0.0 to 1.0 proximity percentage towards a click."""
        if dist <= on_thresh:
            return 1.0
        if dist >= max_range:
            return 0.0
        return max(0.0, min(1.0, (max_range - dist) / (max_range - on_thresh)))

    def detect_pinch(self, raw_dist: float, norm_dist: Optional[float] = None) -> Optional[str]:
        """
        Applies hysteresis to pinch detection:
        - ON when distance drops below pinch_on
        - OFF when distance rises above pinch_off
        """
        is_close = raw_dist < self.pinch_on
        if norm_dist is not None:
            is_close = is_close or (norm_dist < self.pinch_norm_on)

        is_far = raw_dist > self.pinch_off
        if norm_dist is not None:
            is_far = is_far and (norm_dist > self.pinch_norm_off)

        if not self.is_index_pinching and is_close:
            self.is_index_pinching = True
            self.pinch_counter = 1
            return "pinch_start"
        elif self.is_index_pinching:
            if is_far:
                self.is_index_pinching = False
                self.pinch_counter = 0
                return "pinch_end"
            else:
                self.pinch_counter += 1
                return "pinch_hold"
        return None

    def detect_middle_pinch(self, raw_dist: float, norm_dist: Optional[float] = None) -> Optional[str]:
        """Hysteresis for right-click thumb-middle pinch."""
        is_close = raw_dist < self.pinch_on
        if norm_dist is not None:
            is_close = is_close or (norm_dist < self.pinch_norm_on)

        is_far = raw_dist > self.pinch_off
        if norm_dist is not None:
            is_far = is_far and (norm_dist > self.pinch_norm_off)

        if not self.is_middle_pinching and is_close:
            self.is_middle_pinching = True
            return "pinch_start"
        elif self.is_middle_pinching and is_far:
            self.is_middle_pinching = False
            return "pinch_end"
        return "pinch_hold" if self.is_middle_pinching else None

    def can_click(self) -> bool:
        """Enforces click cooldown timer."""
        now = time.time() * 1000.0
        if now - self.last_click_time >= self.click_cooldown_ms:
            self.last_click_time = now
            return True
        return False

    def detect(self, landmarks, timestamp: Optional[float] = None) -> Tuple[str, Dict[str, Any]]:
        """
        Analyzes 21 landmarks and returns (gesture_name, metadata).
        """
        if not landmarks or len(landmarks) < 21:
            self.is_index_pinching = False
            self.is_middle_pinching = False
            self.prev_scroll_y = None
            self.prev_zoom_y = None
            self.wrist_history.clear()
            return "no_hand", {}

        now = timestamp if timestamp is not None else time.time()
        hand_size = self.get_hand_size(landmarks)

        # 1. Update Motion History (for Swipes)
        wrist_pt = landmarks[WRIST]
        wrist_x, wrist_y = wrist_pt.x, wrist_pt.y
        self.wrist_history.append((now, wrist_x, wrist_y))
        # Keep recent 220ms
        self.wrist_history = [p for p in self.wrist_history if (now - p[0]) <= 0.22]

        # Calculate horizontal velocity
        vx = 0.0
        dx = 0.0
        if len(self.wrist_history) >= 2:
            dt = now - self.wrist_history[0][0]
            dx = wrist_x - self.wrist_history[0][1]
            if dt > 0.03:
                vx = dx / dt

        # Raw Euclidean distances in camera space
        raw_thumb_index = euclidean_distance(landmarks[THUMB_TIP], landmarks[INDEX_TIP])
        raw_thumb_middle = euclidean_distance(landmarks[THUMB_TIP], landmarks[MIDDLE_TIP])

        # Hand-scale normalized distances
        norm_thumb_index = raw_thumb_index / hand_size
        norm_thumb_middle = raw_thumb_middle / hand_size

        # Proximity percentages (0.0 to 1.0)
        pinch_proximity = self.calculate_proximity(raw_thumb_index, self.pinch_on, max_range=0.15)
        right_pinch_proximity = self.calculate_proximity(raw_thumb_middle, self.pinch_on, max_range=0.15)

        # Finger extension tests
        index_up = landmarks[INDEX_TIP].y < landmarks[INDEX_PIP].y
        middle_up = landmarks[MIDDLE_TIP].y < landmarks[MIDDLE_PIP].y
        ring_up = landmarks[RING_TIP].y < landmarks[RING_PIP].y
        pinky_up = landmarks[PINKY_TIP].y < landmarks[PINKY_PIP].y

        # Relaxed checks for natural 2-finger peace sign:
        ring_relaxed = landmarks[RING_TIP].y > (landmarks[MIDDLE_TIP].y + 0.035)

        # Fist check: all fingertips below their MCPs
        all_curled = (
            landmarks[INDEX_TIP].y > landmarks[INDEX_MCP].y and
            landmarks[MIDDLE_TIP].y > landmarks[MIDDLE_MCP].y and
            landmarks[RING_TIP].y > landmarks[RING_MCP].y and
            landmarks[PINKY_TIP].y > landmarks[PINKY_MCP].y
        )

        # Open palm check: all fingers extended
        all_extended = index_up and middle_up and ring_up and pinky_up and (raw_thumb_index > 0.12)

        # L-Shape / Zoom pose: Index UP, Thumb OUT, Middle/Ring/Pinky curled
        thumb_spread = euclidean_distance(landmarks[THUMB_TIP], landmarks[INDEX_MCP])
        is_l_shape = (
            index_up and
            not middle_up and
            not ring_up and
            not pinky_up and
            (raw_thumb_index > 0.12) and
            (thumb_spread > 0.075)
        )

        meta = {
            "raw_thumb_index": raw_thumb_index,
            "raw_thumb_middle": raw_thumb_middle,
            "pinch_proximity": pinch_proximity,
            "right_pinch_proximity": right_pinch_proximity,
            "hand_size": hand_size,
            "scroll_mode": False,
            "scroll_delta": 0.0,
            "vx": vx,
            "thumb_tip": (landmarks[THUMB_TIP].x, landmarks[THUMB_TIP].y),
            "index_tip": (landmarks[INDEX_TIP].x, landmarks[INDEX_TIP].y),
            "middle_tip": (landmarks[MIDDLE_TIP].x, landmarks[MIDDLE_TIP].y)
        }

        # -------------------------------------------------------------
        # PRIORITY 1: SWIPES (Next Page / Previous Page)
        # -------------------------------------------------------------
        time_since_swipe = (now * 1000.0) - self.last_swipe_time
        if time_since_swipe > self.swipe_cooldown_ms and abs(vx) > 0.40 and abs(dx) > 0.05:
            self.last_swipe_time = now * 1000.0
            self.prev_scroll_y = None
            self.prev_zoom_y = None
            self.open_palm_start_time = None
            if dx > 0:
                meta["action"] = "next_page"
                return "swipe_right", meta
            else:
                meta["action"] = "prev_page"
                return "swipe_left", meta

        # -------------------------------------------------------------
        # PRIORITY 2: ZOOM IN / ZOOM OUT (L-Shape Pose)
        # -------------------------------------------------------------
        if is_l_shape:
            self.open_palm_start_time = None
            curr_zoom_y = landmarks[INDEX_TIP].y
            time_since_zoom = (now * 1000.0) - self.last_zoom_time
            if self.prev_zoom_y is not None and time_since_zoom > self.zoom_cooldown_ms:
                zoom_dy = self.prev_zoom_y - curr_zoom_y
                if zoom_dy > 0.018:  # Hand moved UP -> Zoom In
                    self.last_zoom_time = now * 1000.0
                    self.prev_zoom_y = curr_zoom_y
                    return "zoom_in", meta
                elif zoom_dy < -0.018:  # Hand moved DOWN -> Zoom Out
                    self.last_zoom_time = now * 1000.0
                    self.prev_zoom_y = curr_zoom_y
                    return "zoom_out", meta
            self.prev_zoom_y = curr_zoom_y
            return "zoom_ready", meta
        else:
            self.prev_zoom_y = None

        # -------------------------------------------------------------
        # PRIORITY 3: PINCHES (Click, Drag, Right-Click)
        # -------------------------------------------------------------
        middle_pinch_state = self.detect_middle_pinch(raw_thumb_middle, norm_thumb_middle)
        if middle_pinch_state == "pinch_start" and self.can_click():
            self.open_palm_start_time = None
            meta["pinch_state"] = "right_click"
            return "thumb_middle_pinch", meta

        index_pinch_state = self.detect_pinch(raw_thumb_index, norm_thumb_index)
        if index_pinch_state:
            self.open_palm_start_time = None
            meta["pinch_state"] = index_pinch_state
            meta["pinch_counter"] = self.pinch_counter
            if index_pinch_state == "pinch_start" and self.can_click():
                return "thumb_index_pinch", meta
            elif index_pinch_state == "pinch_hold":
                if self.pinch_counter >= self.drag_hold_frames:
                    return "drag_hold", meta
                return "thumb_index_pinch", meta
            elif index_pinch_state == "pinch_end":
                return "pinch_release", meta

        # -------------------------------------------------------------
        # PRIORITY 4: PEACE SIGN SCROLLING
        # -------------------------------------------------------------
        if index_up and middle_up and ring_relaxed and raw_thumb_index > self.pinch_off:
            self.open_palm_start_time = None
            raw_gesture = "index_middle_up"
            curr_y = (landmarks[INDEX_TIP].y + landmarks[MIDDLE_TIP].y) / 2.0
            meta["scroll_mode"] = True

            if self.prev_scroll_y is not None:
                delta_y = (self.prev_scroll_y - curr_y)
                # Apply dead-zone to ignore micro-tremors
                if abs(delta_y) > 0.003:
                    meta["scroll_delta"] = delta_y
            self.prev_scroll_y = curr_y
            return "index_middle_up", meta

        # -------------------------------------------------------------
        # PRIORITY 5: OPEN PALM (ONLY if held STILL for 850ms)
        # -------------------------------------------------------------
        if all_extended:
            if abs(vx) < 0.20 and abs(dx) < 0.03:
                if self.open_palm_start_time is None:
                    self.open_palm_start_time = now
                    raw_gesture = "idle"
                elif (now - self.open_palm_start_time) >= self.open_palm_hold_duration_sec:
                    raw_gesture = "open_palm"
                else:
                    raw_gesture = "idle"
            else:
                self.open_palm_start_time = None
                raw_gesture = "idle"
            self.prev_scroll_y = None

        # -------------------------------------------------------------
        # PRIORITY 6: FIST (Neutral / Resume)
        # -------------------------------------------------------------
        elif all_curled:
            self.open_palm_start_time = None
            raw_gesture = "fist"
            self.prev_scroll_y = None

        # -------------------------------------------------------------
        # PRIORITY 7: CURSOR MOVEMENT (Pointing Index Finger)
        # -------------------------------------------------------------
        elif index_up and not middle_up:
            self.open_palm_start_time = None
            raw_gesture = "index_up"
            self.prev_scroll_y = None

        else:
            self.open_palm_start_time = None
            raw_gesture = "idle"
            self.prev_scroll_y = None

        # Fast tracking for cursor movement
        if raw_gesture == "index_up":
            return raw_gesture, meta

        # Stability filtering for discrete transitions
        if raw_gesture == self.candidate_gesture:
            self.consecutive_count += 1
            if self.consecutive_count >= self.required_frames:
                self.current_stable_gesture = raw_gesture
        else:
            self.candidate_gesture = raw_gesture
            self.consecutive_count = 1

        return self.current_stable_gesture, meta
