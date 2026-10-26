"""
Camera Controller for DragonScan Raspberry Pi 5.
Supports Raspberry Pi Camera Module 3 via picamera2 and OpenCV fallback.
"""

import cv2
import numpy as np
import time
import logging
from typing import Optional, Tuple
import config

logger = logging.getLogger(__name__)

class CameraController:
    """
    Manages camera acquisition for Raspberry Pi 5.
    Optimized for Logitech C270 HD Webcam via USB (UVC/V4L2) with 720p 30 FPS MJPG streaming.
    Supports multi-device index auto-discovery and high-fidelity synthetic fallback.
    """
    def __init__(self, width: int = config.CAMERA_WIDTH, height: int = config.CAMERA_HEIGHT, fps: int = config.CAMERA_FPS):
        self.width = width
        self.height = height
        self.fps = fps
        self.is_running = False
        self.backend_type = "NONE"
        self.picam2 = None
        self.cap = None
        self.device_index = getattr(config, "CAMERA_INDEX", 0)
        self.last_frame = None
        self._last_reconnect_time = 0.0

    def _try_connect_usb(self) -> bool:
        """Attempts to discover and connect to a physical USB camera (Logitech C270)."""
        candidate_indices = [self.device_index]
        for idx in [0, 1, 2, 3]:
            if idx not in candidate_indices:
                candidate_indices.append(idx)

        # API backends to try (V4L2 on Linux/Pi, DirectShow on Windows)
        api_backends = []
        if hasattr(cv2, 'CAP_DSHOW'):
            api_backends.append(cv2.CAP_DSHOW)
        if hasattr(cv2, 'CAP_V4L2'):
            api_backends.append(cv2.CAP_V4L2)
        api_backends.append(cv2.CAP_ANY)

        for idx in candidate_indices:
            for api in api_backends:
                try:
                    cap = cv2.VideoCapture(idx, api)
                    if cap.isOpened():
                        # Set MJPG for smooth 30 FPS 720p on Logitech C270
                        try:
                            fourcc = cv2.VideoWriter_fourcc(*'MJPG')
                            cap.set(cv2.CAP_PROP_FOURCC, fourcc)
                        except Exception:
                            pass
                        
                        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                        cap.set(cv2.CAP_PROP_FPS, self.fps)
                        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

                        # Verify frame read
                        ret, test_frame = cap.read()
                        if ret and test_frame is not None and test_frame.size > 0:
                            self.cap = cap
                            self.device_index = idx
                            self.backend_type = "OPENCV"
                            self.is_running = True
                            logger.info(f"Logitech C270 USB Camera connected on device {idx} ({self.width}x{self.height} @ {self.fps}fps).")
                            return True
                        else:
                            cap.release()
                except Exception as e:
                    logger.debug(f"Device index {idx} with backend {api} failed: {e}")
        return False

    def initialize(self) -> bool:
        """Initialize camera driver (prioritizing Logitech C270 USB Webcam)."""
        # 1. Primary: OpenCV VideoCapture for Logitech C270 USB HD Webcam
        if not getattr(config, "USE_PICAMERA2", False):
            if self._try_connect_usb():
                return True

        # 2. Secondary fallback: Picamera2 (if specifically configured for CSI camera)
        if getattr(config, "USE_PICAMERA2", False):
            try:
                from picamera2 import Picamera2
                logger.info("Initializing Picamera2 for CSI Camera...")
                self.picam2 = Picamera2()
                config_cam = self.picam2.create_video_configuration(
                    main={"size": (self.width, self.height), "format": "RGB888"}
                )
                self.picam2.configure(config_cam)
                self.picam2.start()
                self.backend_type = "PICAMERA2"
                self.is_running = True
                logger.info("Picamera2 successfully initialized.")
                return True
            except Exception as e:
                logger.debug(f"Picamera2 init failed: {e}")

        # 3. Clean Standby Mode (Awaiting physical Logitech C270 USB connection)
        logger.warning("No physical USB camera detected on startup. Operating in Optical Standby Mode.")
        self.backend_type = "STANDBY"
        self.is_running = True
        return True

    def get_frame(self) -> Tuple[bool, np.ndarray]:
        """
        Fetch latest BGR frame from real physical camera.
        Returns: (success_bool, bgr_numpy_array)
        """
        if not self.is_running:
            return False, np.zeros((self.height, self.width, 3), dtype=np.uint8)

        # 1. Picamera2 (if CSI camera is active)
        if self.backend_type == "PICAMERA2" and self.picam2:
            try:
                rgb_frame = self.picam2.capture_array()
                bgr_frame = cv2.cvtColor(rgb_frame, cv2.COLOR_RGB2BGR)
                self.last_frame = bgr_frame.copy()
                return True, bgr_frame
            except Exception as e:
                logger.error(f"Error reading frame from Picamera2: {e}")
                return False, np.zeros((self.height, self.width, 3), dtype=np.uint8)

        # 2. Real Physical USB Webcam (Logitech C270 / OpenCV VideoCapture)
        if self.cap is not None and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret and frame is not None and frame.size > 0:
                if frame.shape[0] != self.height or frame.shape[1] != self.width:
                    frame = cv2.resize(frame, (self.width, self.height), interpolation=cv2.INTER_LINEAR)
                self.last_frame = frame.copy()
                return True, frame
            elif self.last_frame is not None:
                return True, self.last_frame.copy()

        # Hot-plug auto-discovery: Periodically attempt to connect if USB camera is plugged in later
        now = time.time()
        if now - self._last_reconnect_time > 2.5:
            self._last_reconnect_time = now
            if self._try_connect_usb() and self.cap is not None:
                ret, frame = self.cap.read()
                if ret and frame is not None and frame.size > 0:
                    if frame.shape[0] != self.height or frame.shape[1] != self.width:
                        frame = cv2.resize(frame, (self.width, self.height), interpolation=cv2.INTER_LINEAR)
                    self.last_frame = frame.copy()
                    return True, frame

        # 3. Clean Optical Cradle Standby Feed (When USB camera is unplugged or initializing)
        frame = self._generate_standby_feed_frame()
        self.last_frame = frame.copy()
        return True, frame

    def capture_snapshot(self) -> Optional[np.ndarray]:
        """Capture single high-fidelity snapshot."""
        ret, frame = self.get_frame()
        if ret:
            return frame
        return self.last_frame

    def _generate_standby_feed_frame(self) -> np.ndarray:
        """
        Generates a clean, professional dark optical bench standby screen.
        Displays alignment crosshairs and hardware connection status without cartoon drawings.
        """
        img = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        # Deep matte obsidian background (scanning chamber interior)
        img[:] = (12, 10, 8)

        cx = self.width // 2
        cy = self.height // 2

        # Subtle optical chamber grid (60px pitch)
        for y in range(0, self.height, 60):
            cv2.line(img, (0, y), (self.width, y), (22, 18, 14), 1)
        for x in range(0, self.width, 60):
            cv2.line(img, (x, 0), (x, self.height), (22, 18, 14), 1)

        # Concentric cradle alignment reticles
        cv2.circle(img, (cx, cy), 220, (35, 28, 20), 1)
        cv2.circle(img, (cx, cy), 150, (45, 36, 26), 1)
        cv2.circle(img, (cx, cy), 70, (55, 44, 32), 1)

        # Center target crosshairs
        cv2.line(img, (cx - 25, cy), (cx + 25, cy), (0, 229, 255), 1)
        cv2.line(img, (cx, cy - 25), (cx, cy + 25), (0, 229, 255), 1)

        # Corner bracket reticles (Chamber boundaries)
        b_len = 35
        # Top-Left
        cv2.line(img, (cx - 180, cy - 120), (cx - 180 + b_len, cy - 120), (0, 229, 255), 2)
        cv2.line(img, (cx - 180, cy - 120), (cx - 180, cy - 120 + b_len), (0, 229, 255), 2)
        # Top-Right
        cv2.line(img, (cx + 180, cy - 120), (cx + 180 - b_len, cy - 120), (0, 229, 255), 2)
        cv2.line(img, (cx + 180, cy - 120), (cx + 180, cy - 120 + b_len), (0, 229, 255), 2)
        # Bottom-Left
        cv2.line(img, (cx - 180, cy + 120), (cx - 180 + b_len, cy + 120), (0, 229, 255), 2)
        cv2.line(img, (cx - 180, cy + 120), (cx - 180, cy + 120 - b_len), (0, 229, 255), 2)
        # Bottom-Right
        cv2.line(img, (cx + 180, cy + 120), (cx + 180 - b_len, cy + 120), (0, 229, 255), 2)
        cv2.line(img, (cx + 180, cy + 120), (cx + 180, cy + 120 - b_len), (0, 229, 255), 2)

        # Status text badges
        cv2.putText(
            img, "LOGITECH C270 USB OPTICAL BENCH - REAL-TIME STANDBY",
            (cx - 280, cy - 140), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 229, 255), 2, cv2.LINE_AA
        )
        cv2.putText(
            img, "CONNECT LOGITECH C270 WEBCAM VIA USB (SEARCHING /dev/video0 OR COM PORT)",
            (cx - 330, cy + 160), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (180, 190, 205), 1, cv2.LINE_AA
        )

        return img

    def release(self):
        """Release camera resources."""
        self.is_running = False
        if self.picam2:
            try:
                self.picam2.stop()
            except Exception:
                pass
            self.picam2 = None
        if self.cap:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None
        logger.info("Camera resources released.")
