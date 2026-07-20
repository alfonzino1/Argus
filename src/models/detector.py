"""
Universal object detector interface with YOLO implementation.
Supports PyTorch, ONNX, and TensorRT backends (via ultralytics).
"""
from abc import ABC, abstractmethod
import time
import logging
from typing import List, Tuple, Optional, Dict, Any
import numpy as np
import torch
from ultralytics import YOLO

logger = logging.getLogger(__name__)


class Detection:
    """Single detection result."""
    __slots__ = ('bbox', 'confidence', 'class_id')
    def __init__(self, bbox: Tuple[int, int, int, int], confidence: float, class_id: int):
        self.bbox = bbox          # (x1, y1, x2, y2) in pixel coordinates
        self.confidence = confidence
        self.class_id = class_id

    def __repr__(self):
        return f"Detection(bbox={self.bbox}, conf={self.confidence:.2f}, class={self.class_id})"


class BaseDetector(ABC):
    """Abstract detector interface."""

    @abstractmethod
    def load_model(self, model_path: str, device: str) -> None:
        """Load model weights and prepare for inference."""
        ...

    @abstractmethod
    def detect(self, frame: np.ndarray) -> List[Detection]:
        """
        Run inference on a BGR frame (HxWx3 numpy array).
        Returns list of Detection objects.
        """
        ...

    @abstractmethod
    def warmup(self, frame_shape: Tuple[int, int, int] = (720, 1280, 3)) -> None:
        """Run a few dummy inferences to initialize GPU/engine."""
        ...


class YOLODetector(BaseDetector):
    """
    YOLO detector using ultralytics library.
    Supports YOLOv8, YOLOv5, YOLOv11, and any model compatible with ultralytics API.
    Configuration dict:
        - model_path: str (e.g., 'yolov8n.pt')
        - confidence_threshold: float (default 0.5)
        - iou_threshold: float (default 0.45)
        - device: str ('cuda', 'cpu', 'mps') or None for auto
        - img_size: int or tuple (default 640)
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = {
            "model_path": "yolov8n.pt",
            "confidence_threshold": 0.5,
            "iou_threshold": 0.45,
            "device": None,  # auto
            "img_size": 640,
        }
        if config:
            self.config.update(config)

        self.model: Optional[YOLO] = None
        self.device: Optional[str] = None

    def load_model(self, model_path: Optional[str] = None, device: Optional[str] = None) -> None:
        """Load YOLO model. Device auto-detection if not specified."""
        if model_path:
            self.config["model_path"] = model_path
        if device:
            self.config["device"] = device

        path = self.config["model_path"]
        dev = self.config["device"]
        if dev is None:
            dev = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = dev

        try:
            logger.info(f"Loading YOLO model from {path} on {dev}")
            self.model = YOLO(path)
            # Ultralytics will move model to device automatically during predict if not set
            # but we can set it explicitly
            self.model.to(dev)
            logger.info("Model loaded successfully")
        except Exception as e:
            logger.exception(f"Failed to load model: {e}")
            raise

    def detect(self, frame: np.ndarray) -> List[Detection]:
        """Run detection on a BGR numpy array."""
        if self.model is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        try:
            start = time.perf_counter()
            results = self.model.predict(
                source=frame,
                conf=self.config["confidence_threshold"],
                iou=self.config["iou_threshold"],
                imgsz=self.config["img_size"],
                device=self.device,
                verbose=False,
                stream=False,  # single image mode
            )
            elapsed = (time.perf_counter() - start) * 1000
            logger.debug(f"Inference time: {elapsed:.1f} ms")

            detections = []
            if results and len(results) > 0:
                result = results[0]  # first (and only) image result
                boxes = result.boxes
                if boxes is not None:
                    for box in boxes:
                        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                        conf = float(box.conf[0])
                        cls_id = int(box.cls[0])
                        detections.append(Detection((x1, y1, x2, y2), conf, cls_id))
            return detections
        except Exception as e:
            logger.exception(f"Error during inference: {e}")
            return []  # fail gracefully, pipeline should handle empty detections

    def warmup(self, frame_shape: Tuple[int, int, int] = (720, 1280, 3)) -> None:
        """Warmup with a random tensor."""
        if self.model is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")
        logger.info("Warming up model...")
        dummy = np.random.randint(0, 255, frame_shape, dtype=np.uint8)
        for _ in range(3):
            _ = self.detect(dummy)
        logger.info("Warmup complete")