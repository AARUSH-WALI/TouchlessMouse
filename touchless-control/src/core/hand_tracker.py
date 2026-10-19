"""Touchless Computer Control System - MediaPipe Hand Tracker Module.

Uses MediaPipe Tasks API (modern vision.HandLandmarker) with VIDEO running mode.
"""

import os
from pathlib import Path
from typing import List, Optional, Tuple
import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# 21 Hand Landmark Connections
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),        # Thumb
    (0, 5), (5, 6), (6, 7), (7, 8),        # Index
    (0, 9), (9, 10), (10, 11), (11, 12),    # Middle
    (0, 13), (13, 14), (14, 15), (15, 16), # Ring
    (0, 17), (17, 18), (18, 19), (19, 20), # Pinky
    (5, 9), (9, 13), (13, 17)              # Palm boundary
]

# Key Landmark Indices
WRIST = 0
THUMB_CMC = 1
THUMB_MCP = 2
THUMB_IP = 3
THUMB_TIP = 4
INDEX_MCP = 5
INDEX_PIP = 6
INDEX_DIP = 7
INDEX_TIP = 8
MIDDLE_MCP = 9
MIDDLE_PIP = 10
MIDDLE_DIP = 11
MIDDLE_TIP = 12
RING_MCP = 13
RING_PIP = 14
RING_DIP = 15
RING_TIP = 16
PINKY_MCP = 17
PINKY_PIP = 18
PINKY_DIP = 19
PINKY_TIP = 20


class HandTracker:
    """
    Wrapper around MediaPipe HandLandmarker Tasks API.
    Processes frames in VIDEO mode with monotonically increasing timestamps.
    """

    def __init__(
        self,
        model_path: str = "models/hand_landmarker.task",
        num_hands: int = 1,
        min_detection_confidence: float = 0.7,
        min_tracking_confidence: float = 0.5,
    ):
        model_file = Path(model_path)
        if not model_file.is_absolute():
            # Resolve relative to project root
            root_dir = Path(__file__).resolve().parent.parent.parent
            model_file = root_dir / model_path

        if not model_file.exists():
            raise FileNotFoundError(
                f"Hand landmarker model not found at {model_file}. "
                f"Please run 'python scripts/download_models.py' first."
            )

        self.model_path = str(model_file)
        self.num_hands = num_hands
        self.min_detection_confidence = min_detection_confidence
        self.min_tracking_confidence = min_tracking_confidence
        self._last_timestamp_ms = -1

        base_options = python.BaseOptions(model_asset_path=self.model_path)
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.VIDEO,
            num_hands=self.num_hands,
            min_hand_detection_confidence=self.min_detection_confidence,
            min_hand_presence_confidence=self.min_tracking_confidence,
            min_tracking_confidence=self.min_tracking_confidence,
        )
        self.detector = vision.HandLandmarker.create_from_options(options)

    def detect(self, frame, timestamp_ms: int):
        """
        Detects hand landmarks in a BGR OpenCV frame.

        Args:
            frame: OpenCV BGR image (numpy array)
            timestamp_ms: monotonically increasing timestamp in milliseconds

        Returns:
            List of hand landmark lists (each containing 21 NormalizedLandmarks)
        """
        if frame is None or frame.size == 0:
            return []

        # Ensure timestamp is strictly monotonically increasing (required by MediaPipe Video mode)
        if timestamp_ms <= self._last_timestamp_ms:
            timestamp_ms = self._last_timestamp_ms + 1
        self._last_timestamp_ms = timestamp_ms

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        result = self.detector.detect_for_video(mp_image, timestamp_ms)
        return result.hand_landmarks if result and result.hand_landmarks else []

    @staticmethod
    def detect_fingers_up(landmarks, left_handed: bool = False) -> List[bool]:
        """
        Returns list of booleans [thumb, index, middle, ring, pinky] indicating
        extended fingers.
        """
        if not landmarks or len(landmarks) < 21:
            return [False, False, False, False, False]

        fingers = []

        # Thumb: lateral movement
        # Right hand in mirrored view: thumb tip is to the left of IP joint if extended
        if left_handed:
            fingers.append(landmarks[THUMB_TIP].x > landmarks[THUMB_IP].x)
        else:
            fingers.append(landmarks[THUMB_TIP].x < landmarks[THUMB_IP].x)

        # 4 fingers: tip is higher (smaller y in image space) than PIP joint
        tip_ids = [INDEX_TIP, MIDDLE_TIP, RING_TIP, PINKY_TIP]
        pip_ids = [INDEX_PIP, MIDDLE_PIP, RING_PIP, PINKY_PIP]

        for tip, pip in zip(tip_ids, pip_ids):
            fingers.append(landmarks[tip].y < landmarks[pip].y)

        return fingers

    @staticmethod
    def draw_landmarks(frame, landmarks, width: int, height: int, is_active: bool = False):
        """
        Draws stylized connections, joints, and cursor pointer landmark.
        """
        if not landmarks or len(landmarks) < 21:
            return

        # 1. Draw connections
        line_color = (0, 230, 115) if is_active else (80, 160, 255)
        for start_idx, end_idx in HAND_CONNECTIONS:
            p1 = landmarks[start_idx]
            p2 = landmarks[end_idx]
            pt1 = (int(p1.x * width), int(p1.y * height))
            pt2 = (int(p2.x * width), int(p2.y * height))
            cv2.line(frame, pt1, pt2, line_color, 2, cv2.LINE_AA)

        # 2. Draw joints
        for i, lm in enumerate(landmarks):
            px, py = int(lm.x * width), int(lm.y * height)
            if i == INDEX_TIP:
                # Primary pointer: glowing double ring
                cv2.circle(frame, (px, py), 9, (0, 255, 255), 2, cv2.LINE_AA)
                cv2.circle(frame, (px, py), 5, (0, 200, 255), -1, cv2.LINE_AA)
            elif i == THUMB_TIP:
                # Pinch detector: bright cyan ring
                cv2.circle(frame, (px, py), 7, (255, 255, 0), 2, cv2.LINE_AA)
                cv2.circle(frame, (px, py), 4, (255, 200, 0), -1, cv2.LINE_AA)
            else:
                cv2.circle(frame, (px, py), 3, (240, 240, 240), -1, cv2.LINE_AA)

    def close(self):
        """Closes detector resources."""
        if hasattr(self, 'detector') and self.detector:
            self.detector.close()
