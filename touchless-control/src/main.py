"""Touchless Computer Control System - Main Application Entry Point.

Integrates camera feed, MediaPipe hand tracking, One Euro Filter cursor smoothing,
rule-based gesture detection, and PyAutoGUI OS action execution with rich visual feedback.
"""

import sys
import time
from pathlib import Path
import cv2
import numpy as np
import pyautogui

# Set path to project root
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.config import Config
from src.core.camera import CameraThread, CameraError
from src.core.hand_tracker import HandTracker, INDEX_TIP, THUMB_TIP, MIDDLE_TIP
from src.core.smoothing import OneEuroFilter
from src.core.gesture_engine import GestureEngine
from src.core.actions import ActionLayer
from src.core.mode_manager import ModeManager
from src.utils.geometry import map_to_screen
from src.utils.logger import setup_logger


class ClickRipple:
    """Animated visual ripple effect on click events."""
    def __init__(self, x: int, y: int, color=(0, 255, 128), max_radius: int = 35):
        self.x = x
        self.y = y
        self.color = color
        self.radius = 8
        self.max_radius = max_radius
        self.alpha = 1.0

    def draw(self, frame):
        if self.radius < self.max_radius:
            cv2.circle(frame, (self.x, self.y), int(self.radius), self.color, 2, cv2.LINE_AA)
            self.radius += 3
            return True
        return False


def draw_hud(
    frame,
    fps: float,
    width: int,
    height: int,
    current_gesture: str,
    mode_name: str,
    is_paused: bool,
    meta: dict,
    show_guide: bool,
    last_action_banner: str,
    active_region: dict = None
):
    """
    Renders a comprehensive, modern HUD with gesture meters, proximity gauges,
    scroll indicators, and an interactive tutorial guide card.
    """
    # 1. Active tracking boundary box
    if active_region:
        left = int(active_region.get("left", 0.15) * width)
        right = int(active_region.get("right", 0.85) * width)
        top = int(active_region.get("top", 0.15) * height)
        bottom = int(active_region.get("bottom", 0.85) * height)

        box_color = (90, 90, 90) if is_paused else (255, 180, 0)
        cv2.rectangle(frame, (left, top), (right, bottom), box_color, 1, cv2.LINE_AA)
        cv2.putText(
            frame,
            "Active Tracking Zone (Screen Area)",
            (left + 8, top + 18),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.42,
            box_color,
            1,
            cv2.LINE_AA
        )

    # 2. Top Banner
    banner_height = 46
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (width, banner_height), (18, 18, 18), -1)
    cv2.addWeighted(overlay, 0.78, frame, 0.22, 0, frame)

    mode_color = (0, 220, 255) if mode_name == "normal" else ((255, 130, 50) if mode_name == "gaming" else (180, 100, 255))
    cv2.putText(
        frame,
        f"Touchless Control | {mode_name.upper()}",
        (14, 28),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        mode_color,
        2,
        cv2.LINE_AA
    )

    # Status / Action text
    if is_paused:
        status_text = "PAUSED (Press 'P' or Open Palm to Resume)"
        status_color = (0, 0, 255)
    elif last_action_banner:
        status_text = last_action_banner
        status_color = (0, 255, 0)
    else:
        status_text = f"Gesture: {current_gesture.replace('_', ' ').title()}"
        status_color = (0, 255, 150) if current_gesture != "idle" else (180, 180, 180)

    cv2.putText(
        frame,
        status_text,
        (260, 28),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.52,
        status_color,
        2,
        cv2.LINE_AA
    )

    # FPS counter
    fps_color = (0, 255, 0) if fps >= 25 else ((0, 200, 255) if fps >= 18 else (0, 0, 255))
    cv2.putText(
        frame,
        f"FPS: {fps:.1f}",
        (width - 105, 28),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        fps_color,
        2,
        cv2.LINE_AA
    )

    # 3. Dynamic Gesture In-Frame Visualizers
    if not is_paused and meta:
        # A) Pinch Distance Meter (Thumb to Index)
        thumb_pt = meta.get("thumb_tip")
        index_pt = meta.get("index_tip")
        if thumb_pt and index_pt:
            tx, ty = int(thumb_pt[0] * width), int(thumb_pt[1] * height)
            ix, iy = int(index_pt[0] * width), int(index_pt[1] * height)
            proximity = meta.get("pinch_proximity", 0.0)

            # Color transitions from cyan (far) to orange (close) to green (pinch!)
            if proximity >= 1.0:
                line_color = (0, 255, 0)      # Neon Green Click
                thickness = 3
                label = "CLICK!"
            elif proximity > 0.6:
                line_color = (0, 180, 255)    # Orange/Yellow Getting Close
                thickness = 2
                label = f"Pinch {int(proximity * 100)}%"
            else:
                line_color = (255, 200, 50)   # Cyan Far
                thickness = 1
                label = f"{int(proximity * 100)}%"

            cv2.line(frame, (tx, ty), (ix, iy), line_color, thickness, cv2.LINE_AA)
            mid_x, mid_y = (tx + ix) // 2, (ty + iy) // 2
            cv2.putText(frame, label, (mid_x - 20, mid_y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.42, line_color, 1, cv2.LINE_AA)

            # Circular target ring around pointer index fingertip
            ring_radius = int(14 - (proximity * 7))  # shrinks from 14 to 7 as fingers pinch
            cv2.circle(frame, (ix, iy), max(6, ring_radius), line_color, 2, cv2.LINE_AA)

        # B) Right-Click Meter (Thumb to Middle)
        middle_pt = meta.get("middle_tip")
        if thumb_pt and middle_pt:
            mx, my = int(middle_pt[0] * width), int(middle_pt[1] * height)
            right_proximity = meta.get("right_pinch_proximity", 0.0)
            if right_proximity > 0.5:
                r_color = (255, 0, 255) if right_proximity >= 1.0 else (200, 100, 255)
                cv2.line(frame, (tx, ty), (mx, my), r_color, 2, cv2.LINE_AA)
                cv2.putText(frame, "R-Click" if right_proximity >= 1.0 else f"{int(right_proximity * 100)}%", (mx + 8, my), cv2.FONT_HERSHEY_SIMPLEX, 0.42, r_color, 1, cv2.LINE_AA)

        # C) Scroll Mode Visual Indicator Widget
        if meta.get("scroll_mode"):
            scroll_delta = meta.get("scroll_delta", 0.0)
            widget_w, widget_h = 280, 48
            wx = (width - widget_w) // 2
            wy = 60

            overlay_scroll = frame.copy()
            cv2.rectangle(overlay_scroll, (wx, wy), (wx + widget_w, wy + widget_h), (25, 25, 25), -1)
            cv2.addWeighted(overlay_scroll, 0.85, frame, 0.15, 0, frame)
            cv2.rectangle(frame, (wx, wy), (wx + widget_w, wy + widget_h), (255, 0, 255), 2, cv2.LINE_AA)

            if scroll_delta > 0.003:
                cv2.putText(frame, "▲▲▲ SCROLLING UP ▲▲▲", (wx + 32, wy + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2, cv2.LINE_AA)
            elif scroll_delta < -0.003:
                cv2.putText(frame, "▼▼▼ SCROLLING DOWN ▼▼▼", (wx + 20, wy + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 220, 255), 2, cv2.LINE_AA)
            else:
                cv2.putText(frame, "◆ 2-FINGER SCROLL READY ◆", (wx + 18, wy + 24), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 0), 1, cv2.LINE_AA)
                cv2.putText(frame, "Move hand UP or DOWN to scroll", (wx + 26, wy + 40), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (200, 200, 200), 1, cv2.LINE_AA)

    # 4. Interactive Gesture Guide Panel (Press 'H' to toggle)
    if show_guide:
        gw, gh = 275, 195
        gx = width - gw - 12
        gy = 55
        overlay_g = frame.copy()
        cv2.rectangle(overlay_g, (gx, gy), (gx + gw, gy + gh), (15, 15, 15), -1)
        cv2.addWeighted(overlay_g, 0.85, frame, 0.15, 0, frame)
        cv2.rectangle(frame, (gx, gy), (gx + gw, gy + gh), (80, 80, 80), 1, cv2.LINE_AA)

        cv2.putText(frame, "GESTURE GUIDE [Press H to hide]", (gx + 12, gy + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (0, 220, 255), 1, cv2.LINE_AA)
        cv2.line(frame, (gx + 10, gy + 24), (gx + gw - 10, gy + 24), (60, 60, 60), 1)

        guide_items = [
            ("Index Point", "Move cursor"),
            ("Pinch Index+Thumb", "Left Click / Drag"),
            ("Pinch Mid+Thumb", "Right Click"),
            ("Swipe Hand ➔ / ⬅", "Next / Prev Page/Slide"),
            ("L-Shape (Gun) Up/Dn", "Zoom In / Zoom Out"),
            ("Peace Sign (2-Up)", "Scroll Up / Down"),
            ("Open Palm (Still)", "Pause Tracking")
        ]

        for i, (title, desc) in enumerate(guide_items):
            row_y = gy + 42 + (i * 21)
            cv2.putText(frame, f"- {title}:", (gx + 8, row_y), cv2.FONT_HERSHEY_SIMPLEX, 0.32, (255, 200, 50), 1, cv2.LINE_AA)
            cv2.putText(frame, desc, (gx + 130, row_y), cv2.FONT_HERSHEY_SIMPLEX, 0.32, (220, 220, 220), 1, cv2.LINE_AA)

    # 5. Bottom Controls Info Bar
    bot_y = height - 26
    overlay_bot = frame.copy()
    cv2.rectangle(overlay_bot, (0, bot_y), (width, height), (18, 18, 18), -1)
    cv2.addWeighted(overlay_bot, 0.78, frame, 0.22, 0, frame)

    cv2.putText(
        frame,
        "Controls: Pinch = Click | Swipe = Page ➔ | ✌ = Scroll | L-Shape = Zoom | 'H' = Guide | 'Q' = Quit",
        (10, height - 8),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.35,
        (220, 220, 220),
        1,
        cv2.LINE_AA
    )


def main():
    # 1. Load Configuration & Setup Logger
    config = Config()
    log_cfg = config.get("logging", {})
    logger = setup_logger(
        log_file=PROJECT_ROOT / log_cfg.get("file", "touchless_control.log"),
        level=log_cfg.get("level", "INFO"),
        max_bytes=log_cfg.get("max_bytes", 5242880),
        backup_count=log_cfg.get("backup_count", 3)
    )

    logger.info("Initializing Touchless Computer Control System...")

    # 2. Hardware and Screen Properties
    screen_w, screen_h = pyautogui.size()
    logger.info(f"Target display screen resolution: {screen_w}x{screen_h}")

    cam_cfg = config.get("camera", {})
    device_index = cam_cfg.get("device_index", 0)
    width = cam_cfg.get("width", 640)
    height = cam_cfg.get("height", 480)
    fps_cap = cam_cfg.get("fps_cap", 30)
    mirror = cam_cfg.get("mirror", True)
    active_region = config.get("cursor.active_region", {})

    # 3. Initialize Filters & Engines
    one_euro_cfg = config.get("cursor.one_euro", {})
    min_cutoff = float(one_euro_cfg.get("min_cutoff", 1.0))
    beta = float(one_euro_cfg.get("beta", 0.007))
    d_cutoff = float(one_euro_cfg.get("d_cutoff", 1.0))

    smoother_x = OneEuroFilter(min_cutoff=min_cutoff, beta=beta, d_cutoff=d_cutoff)
    smoother_y = OneEuroFilter(min_cutoff=min_cutoff, beta=beta, d_cutoff=d_cutoff)

    gesture_engine = GestureEngine(config)
    action_layer = ActionLayer(failsafe_enabled=config.get("failsafe.pyautogui_failsafe", True))
    mode_manager = ModeManager(config)

    # 4. Initialize Hand Tracker
    tracker_cfg = config.get("hand_tracker", {})
    model_path = tracker_cfg.get("model_path", "models/hand_landmarker.task")
    try:
        tracker = HandTracker(
            model_path=model_path,
            num_hands=int(tracker_cfg.get("num_hands", 1)),
            min_detection_confidence=float(tracker_cfg.get("min_detection_confidence", 0.7)),
            min_tracking_confidence=float(tracker_cfg.get("min_tracking_confidence", 0.5))
        )
    except Exception as e:
        logger.error(f"Failed to initialize HandTracker: {e}")
        print(f"\n[ERROR] HandTracker initialization failed: {e}\n")
        sys.exit(1)

    # 5. Initialize & Start Camera Thread
    try:
        camera = CameraThread(
            device_index=device_index,
            width=width,
            height=height,
            fps_cap=fps_cap,
            mirror=mirror
        )
        camera.start()
    except CameraError as e:
        logger.error(f"Camera Initialization Error: {e}")
        print(f"\n[ERROR] {e}\n")
        tracker.close()
        sys.exit(1)

    window_title = "Touchless Computer Control"
    cv2.namedWindow(window_title, cv2.WINDOW_AUTOSIZE)
    logger.info("Camera & tracking loop running. Focus live preview window.")

    # State variables
    current_gesture = "idle"
    frame_count = 0
    modes_list = ["normal", "presentation", "gaming"]
    mode_idx = 0
    show_guide = True
    action_banner = ""
    action_banner_expire = 0.0
    ripples = []
    scroll_accumulator = 0.0
    scroll_sensitivity = float(config.get("gestures.scroll_sensitivity", 5))
    last_pause_time = 0.0

    try:
        while True:
            frame = camera.get_frame(timeout=0.04)
            if frame is None:
                continue

            frame_count += 1
            skip_n = config.get("camera.process_every_n_frames", 1)
            if frame_count % skip_n != 0:
                continue

            timestamp_ms = int(time.monotonic() * 1000)
            hands = tracker.detect(frame, timestamp_ms)

            h, w = frame.shape[:2]
            current_fps = camera.get_fps()
            meta = {}

            if hands:
                landmarks = hands[0]
                # Primary pointer is index fingertip (8)
                pointer = landmarks[INDEX_TIP]
                raw_x, raw_y = pointer.x, pointer.y

                # Map normalized coordinate within active zone to screen space
                screen_x, screen_y = map_to_screen(raw_x, raw_y, active_region, screen_w, screen_h)

                # Filter through One Euro Filter to remove jitter
                smooth_x = smoother_x(screen_x)
                smooth_y = smoother_y(screen_y)

                # Detect gesture
                gesture, meta = gesture_engine.detect(landmarks)
                current_gesture = gesture

                context = {
                    "screen_x": smooth_x,
                    "screen_y": smooth_y,
                    "scroll_delta": meta.get("scroll_delta", 0.0),
                    "landmarks": landmarks
                }

                # Draw stylized hand skeleton on preview
                tracker.draw_landmarks(frame, landmarks, w, h, is_active=(not action_layer.is_paused))

                # Route action through active mode
                action_data = mode_manager.process_gesture(gesture, landmarks, context)
                now = time.time()

                if action_data and not action_layer.is_paused:
                    act = action_data.get("action")
                    if act == "move_cursor":
                        action_layer.move_cursor(action_data["screen_x"], action_data["screen_y"])
                    elif act == "left_click":
                        action_layer.left_click()
                        action_banner = "[ ✓ LEFT CLICK ]"
                        action_banner_expire = now + 0.6
                        ripples.append(ClickRipple(int(pointer.x * w), int(pointer.y * h), color=(0, 255, 0)))
                    elif act == "right_click":
                        action_layer.right_click()
                        action_banner = "[ ✓ RIGHT CLICK ]"
                        action_banner_expire = now + 0.6
                        ripples.append(ClickRipple(int(pointer.x * w), int(pointer.y * h), color=(255, 0, 255)))
                    elif act == "drag_move":
                        action_layer.start_drag()
                        action_layer.move_cursor(action_data["screen_x"], action_data["screen_y"])
                        action_banner = "[ ⚡ DRAGGING ]"
                        action_banner_expire = now + 0.4
                    elif act == "drag_release":
                        action_layer.end_drag()
                        action_banner = "[ ✓ RELEASED ]"
                        action_banner_expire = now + 0.4
                    elif act == "scroll":
                        # Smooth Windows scroll wheel accumulation
                        raw_delta = action_data.get("amount", 0.0)
                        scroll_accumulator += raw_delta * scroll_sensitivity * 1200.0
                        if abs(scroll_accumulator) >= 120.0:
                            # 120 units = 1 notch in Windows WHEEL_DELTA
                            ticks = int(scroll_accumulator / 120.0) * 120
                            action_layer.scroll(ticks)
                            scroll_accumulator -= ticks
                    elif act == "next_page":
                        action_layer.next_page()
                        action_banner = "[ ➔ NEXT PAGE / SLIDE ]"
                        action_banner_expire = now + 0.7
                    elif act == "prev_page":
                        action_layer.prev_page()
                        action_banner = "[ ⬅ PREVIOUS PAGE / SLIDE ]"
                        action_banner_expire = now + 0.7
                    elif act == "zoom_in":
                        action_layer.zoom_in()
                        action_banner = "[ 🔍 ZOOM IN ]"
                        action_banner_expire = now + 0.4
                    elif act == "zoom_out":
                        action_layer.zoom_out()
                        action_banner = "[ 🔍 ZOOM OUT ]"
                        action_banner_expire = now + 0.4
                    elif act == "key_press":
                        action_layer.press_key(action_data.get("key"))
                    elif act == "pause_tracking":
                        if not action_layer.is_paused and (now - last_pause_time > 1.2):
                            action_layer.set_paused(True)
                            last_pause_time = now
                            action_banner = "[ PAUSED (Fist or Point to Resume) ]"
                            action_banner_expire = now + 1.5
                elif action_data and action_layer.is_paused and (now - last_pause_time > 1.2):
                    if action_data.get("action") in ("resume_tracking", "move_cursor", "pause_tracking"):
                        action_layer.set_paused(False)
                        last_pause_time = now
                        action_banner = "[ RESUMED ]"
                        action_banner_expire = now + 1.0

            else:
                current_gesture = "no_hand"
                smoother_x.reset()
                smoother_y.reset()
                scroll_accumulator = 0.0
                if action_layer.is_dragging:
                    action_layer.end_drag()

            # Clean expired banners
            if time.time() > action_banner_expire:
                action_banner = ""

            # Update and render active click ripples
            ripples = [r for r in ripples if r.draw(frame)]

            # Render overlay HUD
            draw_hud(
                frame=frame,
                fps=current_fps,
                width=w,
                height=h,
                current_gesture=current_gesture,
                mode_name=mode_manager.current_mode,
                is_paused=action_layer.is_paused,
                meta=meta,
                show_guide=show_guide,
                last_action_banner=action_banner,
                active_region=active_region
            )

            cv2.imshow(window_title, frame)

            # Keyboard shortcut handler
            key = cv2.waitKey(1) & 0xFF
            if key in (ord('q'), ord('Q'), 27):  # 'q' or ESC to quit
                logger.info("Exit requested by user.")
                break
            elif key in (ord('h'), ord('H')):    # 'h' toggles guide card
                show_guide = not show_guide
            elif key in (ord('p'), ord('P')):    # 'p' toggles pause
                action_layer.toggle_pause()
            elif key in (ord('m'), ord('M')):    # 'm' cycles profile
                mode_idx = (mode_idx + 1) % len(modes_list)
                mode_manager.set_mode(modes_list[mode_idx])

    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt caught.")
    finally:
        logger.info("Cleaning up resources...")
        camera.stop()
        tracker.close()
        cv2.destroyAllWindows()
        logger.info("Touchless Control terminated cleanly.")


if __name__ == "__main__":
    main()
