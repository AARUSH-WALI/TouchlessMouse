"""Touchless Computer Control System - Mode and Profile Manager."""

import time
import logging
from typing import Dict, Any, Optional
from src.core.config import Config

logger = logging.getLogger("touchless.mode_manager")


class ModeManager:
    """
    Handles operating modes (Normal, Presentation, Gaming) and routes
    detected gestures to their profile-mapped actions.
    """

    def __init__(self, config: Config):
        self.config = config
        self.current_mode = config.get("modes.default", "normal")
        self.active_keys = set()
        self.presentation_laser_active = False

    def set_mode(self, mode_name: str):
        """Switches operating profile and reloads mode parameters."""
        available = self.config.get("modes.available", ["normal", "presentation", "gaming"])
        if mode_name not in available:
            logger.warning(f"Unknown mode '{mode_name}'. Available: {available}")
            return False

        self.current_mode = mode_name
        self.config.load_profile(mode_name)
        logger.info(f"Switched to mode: {mode_name}")
        return True

    def process_gesture(self, gesture: str, landmarks: list, context: dict) -> Optional[dict]:
        """
        Translates a detected gesture and coordinates into an executable action payload.

        Returns:
            Dict specifying action and arguments, e.g.
            {'action': 'move_cursor', 'screen_x': x, 'screen_y': y} or None.
        """
        if self.current_mode == "presentation":
            return self._process_presentation(gesture, landmarks, context)
        elif self.current_mode == "gaming":
            return self._process_gaming(gesture, landmarks, context)
        else:
            return self._process_normal(gesture, landmarks, context)

    def _process_normal(self, gesture: str, landmarks: list, context: dict) -> Optional[dict]:
        screen_x = context.get("screen_x", 0)
        screen_y = context.get("screen_y", 0)

        if gesture == "index_up":
            return {"action": "move_cursor", "screen_x": screen_x, "screen_y": screen_y}
        elif gesture == "thumb_index_pinch":
            return {"action": "left_click"}
        elif gesture == "drag_hold":
            return {"action": "drag_move", "screen_x": screen_x, "screen_y": screen_y}
        elif gesture == "pinch_release":
            return {"action": "drag_release"}
        elif gesture == "thumb_middle_pinch":
            return {"action": "right_click"}
        elif gesture == "swipe_right":
            return {"action": "next_page"}
        elif gesture == "swipe_left":
            return {"action": "prev_page"}
        elif gesture == "zoom_in":
            return {"action": "zoom_in"}
        elif gesture == "zoom_out":
            return {"action": "zoom_out"}
        elif gesture == "index_middle_up":
            scroll_delta = context.get("scroll_delta", 0.0)
            if abs(scroll_delta) > 0.002:
                return {"action": "scroll", "amount": scroll_delta}
        elif gesture == "open_palm":
            return {"action": "pause_tracking"}
        elif gesture == "fist":
            return {"action": "resume_tracking"}
        return None

    def _process_presentation(self, gesture: str, landmarks: list, context: dict) -> Optional[dict]:
        if gesture == "index_up":
            return {"action": "laser_pointer", "screen_x": context.get("screen_x"), "screen_y": context.get("screen_y")}
        elif gesture in ("swipe_right", "thumb_index_pinch"):
            return {"action": "next_page"}
        elif gesture in ("swipe_left", "thumb_middle_pinch"):
            return {"action": "prev_page"}
        elif gesture == "zoom_in":
            return {"action": "zoom_in"}
        elif gesture == "zoom_out":
            return {"action": "zoom_out"}
        elif gesture == "fist":
            return {"action": "key_press", "key": "escape"} # End show
        elif gesture == "open_palm":
            return {"action": "pause_tracking"}
        return None

    def _process_gaming(self, gesture: str, landmarks: list, context: dict) -> Optional[dict]:
        if gesture == "thumb_index_pinch":
            return {"action": "key_press", "key": "space"}  # Jump
        elif gesture == "fist":
            return {"action": "left_click"}                 # Attack / trigger
        elif gesture == "swipe_right":
            return {"action": "key_press", "key": "d"}
        elif gesture == "swipe_left":
            return {"action": "key_press", "key": "a"}
        elif gesture == "index_up":
            return {"action": "move_cursor", "screen_x": context.get("screen_x"), "screen_y": context.get("screen_y")}
        return None
