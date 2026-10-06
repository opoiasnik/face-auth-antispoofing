"""Face detection (OpenCV YuNet)."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Protocol

import cv2
import numpy as np

from app.biometrics.types import FaceDetection


class FaceDetector(Protocol):
    def detect(self, image: np.ndarray) -> list[FaceDetection]:
        """Return detected faces sorted by area (largest first)."""
        ...


class YuNetDetector:
    """Lightweight CNN face detector with 5-point landmarks (Wu et al., 2023)."""

    def __init__(
        self, model_path: Path, *, score_threshold: float = 0.85, nms_threshold: float = 0.3
    ) -> None:
        if not model_path.is_file():
            raise FileNotFoundError(model_path)
        self._detector = cv2.FaceDetectorYN.create(
            str(model_path), "", (320, 320), score_threshold, nms_threshold, 50
        )
        # the OpenCV object keeps per-call state (input size) and is not thread-safe
        self._lock = threading.Lock()

    def detect(self, image: np.ndarray) -> list[FaceDetection]:
        h, w = image.shape[:2]
        with self._lock:
            self._detector.setInputSize((w, h))
            _, rows = self._detector.detect(image)
        if rows is None:
            return []
        faces = [FaceDetection.from_yunet(row) for row in rows]
        return sorted(faces, key=lambda f: f.area, reverse=True)
