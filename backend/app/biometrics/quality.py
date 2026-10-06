"""Sample quality assessment (ISO/IEC 29794-5 inspired, simplified)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import cv2
import numpy as np

from app.biometrics.types import FaceDetection, QualityIssue, QualityReport

_SHARPNESS_SIZE = 128


@dataclass(frozen=True, slots=True)
class QualityConfig:
    min_face_size: int
    min_sharpness: float
    min_brightness: float
    max_brightness: float
    secondary_face_area_ratio: float


def _face_crop(image: np.ndarray, face: FaceDetection) -> np.ndarray:
    h, w = image.shape[:2]
    x, y, bw, bh = face.bbox
    x1, y1 = max(int(x), 0), max(int(y), 0)
    x2, y2 = min(int(x + bw), w), min(int(y + bh), h)
    if x2 <= x1 or y2 <= y1:
        return np.zeros((1, 1), dtype=np.uint8)
    return cv2.cvtColor(image[y1:y2, x1:x2], cv2.COLOR_BGR2GRAY)


def sharpness(gray_face: np.ndarray) -> float:
    """Variance of the Laplacian on a size-normalised crop (higher = sharper)."""
    resized = cv2.resize(gray_face, (_SHARPNESS_SIZE, _SHARPNESS_SIZE))
    return float(cv2.Laplacian(resized, cv2.CV_64F).var())


class QualityAssessor:
    def __init__(self, config: QualityConfig) -> None:
        self._config = config

    def assess(self, image: np.ndarray, faces: Sequence[FaceDetection]) -> QualityReport:
        if not faces:
            return QualityReport(issues=(QualityIssue.NO_FACE,))
        cfg = self._config
        main = faces[0]
        issues: list[QualityIssue] = []

        if any(f.area >= main.area * cfg.secondary_face_area_ratio for f in faces[1:]):
            issues.append(QualityIssue.MULTIPLE_FACES)
        if main.min_side < cfg.min_face_size:
            issues.append(QualityIssue.FACE_TOO_SMALL)

        gray = _face_crop(image, main)
        sharp = sharpness(gray)
        bright = float(gray.mean())
        if sharp < cfg.min_sharpness:
            issues.append(QualityIssue.TOO_BLURRY)
        if bright < cfg.min_brightness:
            issues.append(QualityIssue.TOO_DARK)
        elif bright > cfg.max_brightness:
            issues.append(QualityIssue.TOO_BRIGHT)

        return QualityReport(
            issues=tuple(issues), face_size=main.min_side, sharpness=sharp, brightness=bright
        )
