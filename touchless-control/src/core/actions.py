"""Touchless Computer Control System - Action Execution Layer."""

import logging
import pyautogui

logger = logging.getLogger("touchless.actions")

# CRITICAL Performance settings for ultra-responsive cursor movement
pyautogui.PAUSE = 0
pyautogui.FAILSAFE = True


class ActionLayer:
    """
    Executes native OS inputs (mouse moves, clicks, scrolls, drags, key presses)
    with fail-safe protection and error recovery.
    """

    def __init__(self, failsafe_enabled: bool = True):
        pyautogui.FAILSAFE = failsafe_enabled
        self.is_dragging = False
        self.is_paused = False
        self.screen_width, self.screen_height = pyautogui.size()
        logger.info(f"ActionLayer initialized for screen {self.screen_width}x{self.screen_height}")

    def move_cursor(self, screen_x: float, screen_y: float):
        """Moves cursor to screen pixel coordinates without delay."""
        if self.is_paused:
            return
        try:
            pyautogui.moveTo(int(screen_x), int(screen_y), _pause=False)
        except pyautogui.FailSafeException:
            logger.warning("PyAutoGUI FailSafe triggered (cursor at screen corner). Pausing tracking.")
            self.is_paused = True
        except Exception as e:
            logger.error(f"Error moving cursor: {e}")

    def left_click(self):
        """Executes a left mouse click."""
        if self.is_paused:
            return
        try:
            pyautogui.click()
            logger.debug("Left click executed.")
        except pyautogui.FailSafeException:
            logger.warning("PyAutoGUI FailSafe triggered on click. Pausing tracking.")
            self.is_paused = True
        except Exception as e:
            logger.error(f"Error executing left click: {e}")

    def right_click(self):
        """Executes a right mouse click."""
        if self.is_paused:
            return
        try:
            pyautogui.rightClick()
            logger.debug("Right click executed.")
        except pyautogui.FailSafeException:
            logger.warning("PyAutoGUI FailSafe triggered on right click. Pausing tracking.")
            self.is_paused = True
        except Exception as e:
            logger.error(f"Error executing right click: {e}")

    def double_click(self):
        """Executes a double click."""
        if self.is_paused:
            return
        try:
            pyautogui.doubleClick()
            logger.debug("Double click executed.")
        except pyautogui.FailSafeException:
            logger.warning("PyAutoGUI FailSafe triggered. Pausing tracking.")
            self.is_paused = True
        except Exception as e:
            logger.error(f"Error executing double click: {e}")

    def start_drag(self):
        """Presses and holds the left mouse button for dragging."""
        if self.is_paused or self.is_dragging:
            return
        try:
            pyautogui.mouseDown()
            self.is_dragging = True
            logger.debug("Drag started (mouseDown).")
        except pyautogui.FailSafeException:
            logger.warning("PyAutoGUI FailSafe triggered on drag. Pausing tracking.")
            self.is_paused = True
        except Exception as e:
            logger.error(f"Error starting drag: {e}")

    def end_drag(self):
        """Releases the left mouse button."""
        if not self.is_dragging:
            return
        try:
            pyautogui.mouseUp()
            self.is_dragging = False
            logger.debug("Drag released (mouseUp).")
        except pyautogui.FailSafeException:
            logger.warning("PyAutoGUI FailSafe triggered on drag end. Pausing tracking.")
            self.is_paused = True
        except Exception as e:
            logger.error(f"Error releasing drag: {e}")

    def scroll(self, amount: int):
        """Scrolls vertically (positive = up, negative = down)."""
        if self.is_paused or amount == 0:
            return
        try:
            pyautogui.scroll(int(amount))
            logger.debug(f"Scroll executed: {amount}")
        except pyautogui.FailSafeException:
            logger.warning("PyAutoGUI FailSafe triggered on scroll. Pausing tracking.")
            self.is_paused = True
        except Exception as e:
            logger.error(f"Error executing scroll: {e}")

    def press_key(self, key: str):
        """Presses a single keyboard key."""
        if self.is_paused:
            return
        try:
            pyautogui.press(key)
            logger.debug(f"Key press executed: {key}")
        except Exception as e:
            logger.error(f"Error executing key press: {e}")

    def hotkey(self, *keys):
        """Triggers a keyboard shortcut sequence, e.g. ('ctrl', 'c')."""
        if self.is_paused:
            return
        try:
            pyautogui.hotkey(*keys)
            logger.debug(f"Hotkey executed: {keys}")
        except Exception as e:
            logger.error(f"Error executing hotkey: {e}")

    def next_page(self):
        """Advances to next slide or page in PowerPoint, PDF, or browser."""
        if self.is_paused:
            return
        try:
            pyautogui.press('right')
            logger.debug("Next page executed (Right Arrow).")
        except Exception as e:
            logger.error(f"Error executing next page: {e}")

    def prev_page(self):
        """Returns to previous slide or page."""
        if self.is_paused:
            return
        try:
            pyautogui.press('left')
            logger.debug("Previous page executed (Left Arrow).")
        except Exception as e:
            logger.error(f"Error executing previous page: {e}")

    def zoom_in(self):
        """Zooms into active document or application (Ctrl + =)."""
        if self.is_paused:
            return
        try:
            pyautogui.hotkey('ctrl', '=')
            logger.debug("Zoom in executed.")
        except Exception as e:
            logger.error(f"Error executing zoom in: {e}")

    def zoom_out(self):
        """Zooms out active document or application (Ctrl + Minus)."""
        if self.is_paused:
            return
        try:
            pyautogui.hotkey('ctrl', '-')
            logger.debug("Zoom out executed.")
        except Exception as e:
            logger.error(f"Error executing zoom out: {e}")

    def toggle_pause(self):
        """Toggles tracking pause on/off."""
        self.is_paused = not self.is_paused
        if self.is_dragging:
            self.end_drag()
        logger.info(f"Tracking pause state: {self.is_paused}")
        return self.is_paused

    def set_paused(self, paused: bool):
        self.is_paused = paused
        if self.is_dragging:
            self.end_drag()
