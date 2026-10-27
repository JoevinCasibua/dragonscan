"""
YOLOv11 / COCO Deep Learning Object Detection Engine for DragonScan.
Supports YOLOv11 (yolo11n.pt / coco.pt / custom dragonfruit weights) on Raspberry Pi 5.
Provides deep learning bounding box localization, confidence scoring, and segmentation
with seamless fallback to OpenCV classical segmentation if PyTorch/Ultralytics is unavailable.
"""

import logging
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List
import numpy as np
import cv2
import config

logger = logging.getLogger(__name__)

class YoloDetector:
    """
    Integrates YOLOv11 / YOLOv8 / COCO object detection models into DragonScan.
    Optimized for Raspberry Pi 5 ARM Cortex-A76 CPU or Coral/NCNN accelerators.
    """
    def __init__(self, model_name_or_path: str = "yolo11n.pt"):
        self.model_path = config.MODELS_DIR / model_name_or_path if not Path(model_name_or_path).is_absolute() else Path(model_name_or_path)
        self.model_name = model_name_or_path
        self.is_loaded = False
        self.model = None
        self.backend = "OPENCV_FALLBACK"
        self._initialize_model()

    def _initialize_model(self):
        """Attempts to load Ultralytics YOLO model or prepares graceful fallback."""
        if not getattr(config, "USE_YOLO_IF_AVAILABLE", False):
            self.backend = "OPENCV_FALLBACK"
            self.is_loaded = False
            return

        try:
            from ultralytics import YOLO
            # 1. Check if model exists locally in models directory, otherwise download/load
            model_target = str(self.model_path) if self.model_path.exists() else self.model_name
            logger.info(f"Loading YOLO model: {model_target}...")
            self.model = YOLO(model_target)
            self.is_loaded = True
            self.backend = "ULTRALYTICS_YOLO"
            logger.info(f"YOLO model ({self.model_name}) successfully loaded on {self.backend}.")
        except ImportError:
            logger.info("Ultralytics library not installed. Operating with OpenCV classical segmentation.")
            self.backend = "OPENCV_FALLBACK"
            self.is_loaded = False
        except Exception as e:
            logger.warning(f"Could not load YOLO model ({e}). Using OpenCV classical segmentation.")
            self.backend = "OPENCV_FALLBACK"
            self.is_loaded = False

    def detect_fruit(self, bgr_image: np.ndarray, conf_threshold: float = 0.35) -> Dict[str, Any]:
        """
        Runs YOLO detection on a BGR image frame.
        Returns fruit bounding box, confidence score, and detection status.
        """
        if not self.is_loaded or self.model is None:
            return {
                "detected": False,
                "backend": self.backend,
                "confidence": 0.0,
                "bbox": None,
                "label": "None",
                "boxes": []
            }

        try:
            # Run inference
            results = self.model(bgr_image, conf=conf_threshold, verbose=False)
            if not results or len(results) == 0:
                return {
                    "detected": False,
                    "backend": self.backend,
                    "confidence": 0.0,
                    "bbox": None,
                    "label": "None",
                    "boxes": []
                }

            boxes = results[0].boxes
            if len(boxes) == 0:
                return {
                    "detected": False,
                    "backend": self.backend,
                    "confidence": 0.0,
                    "bbox": None,
                    "label": "None",
                    "boxes": []
                }

            # Pick detection with highest confidence (or largest area)
            best_box = None
            max_conf = 0.0
            best_coords = None
            best_label = "fruit"

            EXCLUDED_CLASSES = {"person", "human", "chair", "bed", "couch", "laptop", "cell phone", "keyboard", "tv", "monitor"}

            parsed_boxes = []
            for b in boxes:
                xyxy = b.xyxy[0].cpu().numpy().astype(int)
                conf = float(b.conf[0].cpu().numpy())
                cls_idx = int(b.cls[0].cpu().numpy())
                cls_name = results[0].names.get(cls_idx, "object")

                parsed_boxes.append({
                    "bbox": xyxy.tolist(),
                    "confidence": round(conf, 3),
                    "class": cls_name
                })

                if cls_name.lower() in EXCLUDED_CLASSES:
                    continue

                if conf > max_conf:
                    max_conf = conf
                    best_coords = xyxy
                    best_label = cls_name

            if best_coords is None:
                return {
                    "detected": False,
                    "backend": self.backend,
                    "confidence": 0.0,
                    "bbox": None,
                    "label": "None",
                    "boxes": parsed_boxes
                }

            x1, y1, x2, y2 = best_coords
            w = x2 - x1
            h = y2 - y1

            # All detected agricultural/fruit candidates in DragonScan are designated as dragonfruit
            FRUIT_MAPPINGS = {"banana", "apple", "orange", "broccoli", "carrot", "potted plant", "bird", "bowl", "vase", "fruit", "object"}
            target_label = "dragonfruit" if best_label.lower() in FRUIT_MAPPINGS else best_label

            return {
                "detected": True,
                "backend": self.backend,
                "confidence": round(max_conf * 100.0, 1),
                "bbox": (int(x1), int(y1), int(w), int(h)),
                "label": target_label,
                "boxes": parsed_boxes
            }

        except Exception as e:
            logger.error(f"Error during YOLO inference: {e}")
            return {
                "detected": False,
                "backend": self.backend,
                "confidence": 0.0,
                "bbox": None,
                "label": "Error",
                "boxes": []
            }
