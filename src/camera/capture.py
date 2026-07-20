"""
Production-ready camera capture with auto-reconnect and threaded reading.
"""
import time
import threading
import logging
from typing import Optional, Tuple, Dict, Any
import cv2
import numpy as np

logger = logging.getLogger(__name__)


class CameraStream:
    """
    Thread-safe video capture from USB camera, RTSP stream, or video file.
    Automatically reconnects on failure and skips corrupted frames.

    Parameters
    ----------
    source : int or str
        Device index (0, 1) or RTSP URL or file path.
    config : dict, optional
        Configuration dictionary with keys:
            - width (int): frame width, default 1280
            - height (int): frame height, default 720
            - fps (int): target FPS, default 30
            - backend (str): OpenCV backend, e.g. "CAP_ANY", "CAP_V4L2", default "CAP_ANY"
            - reconnect_attempts (int): max reconnect retries, -1 for infinite, default 10
            - reconnect_delay (float): seconds between reconnect attempts, default 2.0
            - buffer_size (int): max frame queue size, default 1
    """

    def __init__(
        self,
        source: int = 0,
        config: Optional[Dict[str, Any]] = None
    ):
        self.source = source
        # Default configuration
        self.config = {
            "width": 1280,
            "height": 720,
            "fps": 30,
            "backend": "CAP_ANY",
            "reconnect_attempts": 10,
            "reconnect_delay": 2.0,
            "buffer_size": 1,
        }
        if config:
            self.config.update(config)

        self.cap: Optional[cv2.VideoCapture] = None
        self.frame: Optional[np.ndarray] = None
        self.is_running = False
        self.thread: Optional[threading.Thread] = None
        self.lock = threading.Lock()
        self._backend = getattr(cv2, self.config["backend"], cv2.CAP_ANY)
        self._reconnect_attempts = self.config["reconnect_attempts"]
        self._reconnect_delay = self.config["reconnect_delay"]

    def _open_capture(self) -> bool:
        """Attempt to open video source. Returns True on success."""
        try:
            if self.cap is not None:
                self.cap.release()
            self.cap = cv2.VideoCapture(self.source, self._backend)
            if not self.cap.isOpened():
                logger.error(f"Cannot open source: {self.source}")
                return False

            # Apply configuration
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.config["width"])
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config["height"])
            self.cap.set(cv2.CAP_PROP_FPS, self.config["fps"])

            # Read one test frame to verify stream is alive
            ret, _ = self.cap.read()
            if not ret:
                logger.warning("Stream opened but no frame received")
                self.cap.release()
                return False

            logger.info(
                f"Camera opened: {self.source} "
                f"{self.config['width']}x{self.config['height']} @ {self.config['fps']}fps"
            )
            return True
        except Exception as e:
            logger.exception(f"Error opening camera: {e}")
            return False

    def _reconnect_loop(self) -> bool:
        """Keep trying to reconnect until success or attempts exhausted."""
        attempts = 0
        while self._reconnect_attempts == -1 or attempts < self._reconnect_attempts:
            logger.info(f"Reconnection attempt {attempts + 1}...")
            if self._open_capture():
                return True
            attempts += 1
            time.sleep(self._reconnect_delay)
        logger.critical(f"Failed to reconnect after {attempts} attempts")
        return False

    def _reader_thread(self):
        """Thread target: continuously read frames with reconnection."""
        while self.is_running:
            if self.cap is None or not self.cap.isOpened():
                # Attempt to reconnect
                if not self._reconnect_loop():
                    self.is_running = False
                    break

            try:
                ret, frame = self.cap.read()
                if not ret:
                    logger.warning("Failed to read frame, may need reconnection")
                    # Try to reopen on next iteration
                    if self.cap:
                        self.cap.release()
                    self.cap = None
                    time.sleep(self._reconnect_delay)
                    continue

                # Update the latest frame in a thread-safe manner
                with self.lock:
                    self.frame = frame
            except Exception as e:
                logger.exception(f"Error in reader thread: {e}")
                # Prevent tight loop on repeated errors
                time.sleep(0.1)

    def start(self) -> bool:
        """
        Start the capture thread.
        Returns True if the stream was successfully started.
        """
        if self.is_running:
            logger.warning("Camera already running")
            return True

        if not self._open_capture():
            logger.error("Initial camera open failed")
            return False

        self.is_running = True
        self.thread = threading.Thread(target=self._reader_thread, daemon=True)
        self.thread.start()
        logger.info("Camera stream started")
        return True

    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        """
        Get the latest frame.
        Returns (True, frame) if available, else (False, None).
        Non-blocking; if no frame is ready yet, returns the last one.
        """
        if not self.is_running:
            return False, None
        with self.lock:
            if self.frame is None:
                return False, None
            # Return a copy to avoid external modification
            return True, self.frame.copy()

    def stop(self):
        """Gracefully stop the capture thread and release resources."""
        self.is_running = False
        if self.thread is not None:
            self.thread.join(timeout=5.0)
            self.thread = None
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        logger.info("Camera stream stopped")

    @property
    def is_opened(self) -> bool:
        return self.cap is not None and self.cap.isOpened() and self.is_running

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()