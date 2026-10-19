"""Touchless Computer Control System - Threaded Camera Module."""

import cv2
import time
import queue
import threading
import logging

logger = logging.getLogger("touchless.camera")


class CameraError(Exception):
    """Custom exception raised for camera acquisition or hardware failures."""
    pass


class CameraThread(threading.Thread):
    """
    Asynchronous camera capture thread running at a target FPS and resolution.
    Drops old frames to maintain low latency (zero frame buildup).
    """

    def __init__(self, device_index=0, width=640, height=480, fps_cap=30, mirror=True):
        super().__init__(name="CameraThread", daemon=True)
        self.device_index = device_index
        self.target_width = width
        self.target_height = height
        self.fps_cap = fps_cap
        self.mirror = mirror
        
        self.frame_queue = queue.Queue(maxsize=2)
        self.running = False
        self._stopped_event = threading.Event()
        
        # Performance & FPS stats
        self.actual_width = 0
        self.actual_height = 0
        self.actual_fps = 0.0
        self.fps = 0.0
        self._frame_count = 0
        self._fps_start_time = time.time()

        # Initialize hardware capture
        self.cap = cv2.VideoCapture(self.device_index, cv2.CAP_DSHOW if cv2.__file__ and "win" in cv2.__file__.lower() else cv2.CAP_ANY)
        if not self.cap.isOpened():
            # Fallback to default backend if DSHOW fails
            self.cap = cv2.VideoCapture(self.device_index)

        if not self.cap.isOpened():
            raise CameraError(
                f"Cannot open camera index {self.device_index}. "
                f"Verify that a webcam is connected and not currently used by another application."
            )

        # Set hardware properties
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.target_width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.target_height)
        self.cap.set(cv2.CAP_PROP_FPS, self.fps_cap)

        # Query actual hardware values
        self.actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.actual_fps = float(self.cap.get(cv2.CAP_PROP_FPS))

        logger.info(
            f"Camera #{self.device_index} initialized: "
            f"Requested: {self.target_width}x{self.target_height} @ {self.fps_cap}fps | "
            f"Actual: {self.actual_width}x{self.actual_height} @ {self.actual_fps:.1f}fps | "
            f"Mirror: {self.mirror}"
        )

    def start(self):
        self.running = True
        self._fps_start_time = time.time()
        self._frame_count = 0
        super().start()

    def run(self):
        """Worker loop continuously capturing and pushing frames."""
        frame_interval = 1.0 / self.fps_cap if self.fps_cap > 0 else 0.033
        
        while self.running:
            loop_start = time.time()
            
            if not self.cap or not self.cap.isOpened():
                logger.error("Camera device lost or closed during execution.")
                break

            ret, frame = self.cap.read()
            if not ret or frame is None:
                # Brief sleep to prevent tight looping on transient read drops
                time.sleep(0.005)
                continue

            # Mirror horizontally if requested
            if self.mirror:
                frame = cv2.flip(frame, 1)

            # Drop older frames if queue is full to avoid latency accumulation
            if self.frame_queue.full():
                try:
                    self.frame_queue.get_nowait()
                except queue.Empty:
                    pass

            try:
                self.frame_queue.put_nowait(frame)
            except queue.Full:
                pass

            # Update FPS tracking
            self._frame_count += 1
            if self._frame_count >= 15:
                elapsed = time.time() - self._fps_start_time
                if elapsed > 0:
                    self.fps = self._frame_count / elapsed
                self._frame_count = 0
                self._fps_start_time = time.time()

            # Enforce FPS cap
            process_time = time.time() - loop_start
            sleep_duration = frame_interval - process_time
            if sleep_duration > 0.001:
                time.sleep(sleep_duration)

        self._cleanup()
        self._stopped_event.set()

    def get_frame(self, timeout=0.03):
        """
        Retrieves the latest captured frame.
        Returns None if no frame is available within timeout.
        """
        try:
            return self.frame_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def get_fps(self):
        """Returns the measured running FPS of the camera capture."""
        return self.fps

    def stop(self):
        """Signals thread to stop and waits for clean hardware release."""
        self.running = False
        self._stopped_event.wait(timeout=2.0)
        self._cleanup()

    def _cleanup(self):
        if self.cap is not None and self.cap.isOpened():
            self.cap.release()
            self.cap = None
            logger.info("Camera device released cleanly.")
