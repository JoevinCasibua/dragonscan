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
    Auto-detects picamera2 (Pi Camera Module 3) or falls back to cv2.VideoCapture.
    """
    def __init__(self, width: int = config.CAMERA_WIDTH, height: int = config.CAMERA_HEIGHT, fps: int = config.CAMERA_FPS):
        self.width = width
        self.height = height
        self.fps = fps
        self.is_running = False
        self.backend_type = "NONE"
        self.picam2 = None
        self.cap = None
        self.last_frame = None

    def initialize(self) -> bool:
        """Initialize camera driver."""
        # 1. Try picamera2 (Standard on Raspberry Pi OS Bookworm with Pi 5)
        if config.USE_PICAMERA2:
            try:
                from picamera2 import Picamera2
                logger.info("Initializing Picamera2 for Camera Module 3...")
                self.picam2 = Picamera2()
                config_cam = self.picam2.create_video_configuration(
                    main={"size": (self.width, self.height), "format": "RGB888"}
                )
                self.picam2.configure(config_cam)
                self.picam2.start()
                
                # Lock controls if requested
                if config.CAMERA_EXPOSURE_LOCKED:
                    try:
                        self.picam2.set_controls({"AeEnable": False, "ExposureTime": 15000})
                    except Exception as e:
                        logger.warning(f"Could not lock exposure: {e}")
                
                self.backend_type = "PICAMERA2"
                self.is_running = True
                logger.info("Picamera2 successfully initialized.")
                return True
            except (ImportError, Exception) as e:
                logger.info(f"Picamera2 not available ({e}). Falling back to OpenCV VideoCapture.")

        # 2. Try OpenCV VideoCapture (Standard USB / V4L2 / Laptop webcam fallback)
        try:
            self.cap = cv2.VideoCapture(config.CAMERA_INDEX, cv2.CAP_DSHOW if hasattr(cv2, 'CAP_DSHOW') else cv2.CAP_ANY)
            if self.cap.isOpened():
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                self.cap.set(cv2.CAP_PROP_FPS, self.fps)
                self.backend_type = "OPENCV"
                self.is_running = True
                logger.info(f"OpenCV camera initialized on device {config.CAMERA_INDEX}.")
                return True
        except Exception as e:
            logger.warning(f"OpenCV camera init failed: {e}")

        # 3. Synthetic frame generator fallback (allows running app without hardware connected)
        logger.warning("No physical camera detected. Operating in Synthetic Frame Simulation Mode.")
        self.backend_type = "SYNTHETIC"
        self.is_running = True
        return True

    def get_frame(self) -> Tuple[bool, np.ndarray]:
        """
        Fetch latest BGR frame from camera.
        Returns: (success_bool, bgr_numpy_array)
        """
        if not self.is_running:
            return False, np.zeros((self.height, self.width, 3), dtype=np.uint8)

        if self.backend_type == "PICAMERA2" and self.picam2:
            try:
                rgb_frame = self.picam2.capture_array()
                bgr_frame = cv2.cvtColor(rgb_frame, cv2.COLOR_RGB2BGR)
                self.last_frame = bgr_frame.copy()
                return True, bgr_frame
            except Exception as e:
                logger.error(f"Error reading frame from Picamera2: {e}")
                return False, np.zeros((self.height, self.width, 3), dtype=np.uint8)

        elif self.backend_type == "OPENCV" and self.cap:
            ret, frame = self.cap.read()
            if ret and frame is not None:
                self.last_frame = frame.copy()
                return True, frame
            else:
                return False, np.zeros((self.height, self.width, 3), dtype=np.uint8)

        else:
            # Generate animated synthetic dragon fruit test stream
            frame = self._generate_synthetic_dragonfruit_frame()
            self.last_frame = frame.copy()
            return True, frame

    def capture_snapshot(self) -> Optional[np.ndarray]:
        """Capture single high-fidelity snapshot."""
        ret, frame = self.get_frame()
        if ret:
            return frame
        return self.last_frame

    def _generate_synthetic_dragonfruit_frame(self) -> np.ndarray:
        """Generates dynamic synthetic sample frame with fruit on scanning stage."""
        img = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        # Deep obsidian aerospace cradle background
        img[:] = (18, 14, 10)

        # High-tech circular cradle alignment guides
        center_x = self.width // 2
        center_y = self.height // 2

        # Precision cradle grid
        for y in range(0, self.height, 60):
            cv2.line(img, (0, y), (self.width, y), (28, 24, 20), 1)
        for x in range(0, self.width, 60):
            cv2.line(img, (x, 0), (x, self.height), (28, 24, 20), 1)

        # Concentric optical bench cradle rings
        cv2.circle(img, (center_x, center_y), 220, (38, 32, 26), 1)
        cv2.circle(img, (center_x, center_y), 150, (48, 40, 32), 1)

        t = time.time()
        pulse = int(12 * np.sin(t * 2.5))

        # 45-degree radar beam visualization
        radar_x = int(center_x - 220 + 20 * np.cos(t * 2))
        radar_y = int(center_y - 180 + 20 * np.sin(t * 2))
        cv2.line(img, (radar_x, radar_y), (center_x, center_y), (0, 180, 255), 1)

        # Dragon fruit outer body (Vibrant Red-Violet / Magenta peel)
        fruit_axes = (165 + pulse // 3, 115)
        # Layered glow
        cv2.ellipse(img, (center_x, center_y), (fruit_axes[0] + 6, fruit_axes[1] + 6), 12, 0, 360, (70, 10, 140), -1)
        cv2.ellipse(img, (center_x, center_y), fruit_axes, 12, 0, 360, (110, 25, 210), -1)
        # Inner core gradient
        cv2.ellipse(img, (center_x - 10, center_y - 10), (fruit_axes[0] - 25, fruit_axes[1] - 20), 12, 0, 360, (130, 35, 230), -1)

        # Leafy Bracts (Yellow-Green fleshy scales with curled tips)
        for angle in range(0, 360, 40):
            rad = np.deg2rad(angle + 12)
            bx = int(center_x + (fruit_axes[0] * 0.92) * np.cos(rad))
            by = int(center_y + (fruit_axes[1] * 0.92) * np.sin(rad))
            cv2.circle(img, (bx, by), 18, (45, 185, 95), -1)
            cv2.circle(img, (bx, by), 12, (60, 220, 130), -1)
            # Tip
            tip_x = int(bx + 10 * np.cos(rad))
            tip_y = int(by + 10 * np.sin(rad))
            cv2.circle(img, (tip_x, tip_y), 5, (80, 240, 220), -1)

        # Sunken necrotic rot lesion patch with dark concentric decay rings
        rot_center = (center_x + 35, center_y - 25)
        cv2.circle(img, rot_center, 44, (18, 30, 40), -1)
        cv2.circle(img, rot_center, 30, (12, 20, 28), -1)
        cv2.circle(img, rot_center, 15, (6, 10, 16), -1)

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
