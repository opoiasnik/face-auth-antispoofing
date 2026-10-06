"""Passive (single-frame) presentation attack detection with MiniFASNet models.

Models originate from Silent-Face-Anti-Spoofing (Minivision) and are run via
ONNX Runtime. Each model sees a face crop enlarged by its own ``crop_scale``
(more context helps to spot screen bezels, paper edges and moiré patterns).
The input is BGR, float32 in range 0-255, NCHW. Output class 1 means "live".
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import cv2
import numpy as np
import onnxruntime as ort

from app.biometrics.types import FaceDetection

logger = logging.getLogger(__name__)

LIVE_CLASS_INDEX = 1
_DEFAULT_INPUT_SIZE = (80, 80)


class PassiveLivenessDetector(Protocol):
    def score(self, image: np.ndarray, face: FaceDetection) -> float:
        """Return the probability (0-1) that the face is a live presentation."""
        ...


@dataclass(frozen=True, slots=True)
class AntiSpoofModelSpec:
    path: Path
    crop_scale: float
    weight: float = 1.0


def crop_with_context(
    image: np.ndarray, bbox: tuple[float, float, float, float], scale: float, size: tuple[int, int]
) -> np.ndarray:
    """Crop a square-ish region ``scale`` times larger than the bbox, clipped to the image."""
    src_h, src_w = image.shape[:2]
    x, y, box_w, box_h = bbox
    box_w, box_h = max(box_w, 1.0), max(box_h, 1.0)
    scale = min((src_h - 1) / box_h, (src_w - 1) / box_w, scale)
    new_w, new_h = box_w * scale, box_h * scale
    cx, cy = x + box_w / 2, y + box_h / 2

    x1 = max(0, int(cx - new_w / 2))
    y1 = max(0, int(cy - new_h / 2))
    x2 = min(src_w - 1, int(cx + new_w / 2))
    y2 = min(src_h - 1, int(cy + new_h / 2))
    crop = image[y1 : y2 + 1, x1 : x2 + 1]
    height, width = size
    return cv2.resize(crop, (width, height))


def _softmax(logits: np.ndarray) -> np.ndarray:
    shifted = np.exp(logits - np.max(logits, axis=-1, keepdims=True))
    return shifted / shifted.sum(axis=-1, keepdims=True)


class _OnnxModel:
    def __init__(self, spec: AntiSpoofModelSpec, providers: Sequence[str]) -> None:
        if not spec.path.is_file():
            raise FileNotFoundError(spec.path)
        options = ort.SessionOptions()
        options.intra_op_num_threads = 2
        self.session = ort.InferenceSession(
            str(spec.path), sess_options=options, providers=list(providers)
        )
        model_input = self.session.get_inputs()[0]
        self.input_name = model_input.name
        dims = model_input.shape[2:]
        self.input_size: tuple[int, int] = (
            (int(dims[0]), int(dims[1]))
            if all(isinstance(d, int) for d in dims)
            else _DEFAULT_INPUT_SIZE
        )
        self.spec = spec

    def live_probability(self, image: np.ndarray, face: FaceDetection) -> float:
        crop = crop_with_context(image, face.bbox, self.spec.crop_scale, self.input_size)
        tensor = np.transpose(crop.astype(np.float32), (2, 0, 1))[np.newaxis, ...]
        logits = self.session.run(None, {self.input_name: tensor})[0]
        return float(_softmax(logits)[0, LIVE_CLASS_INDEX])


class MiniFASNetEnsemble:
    """Weighted average of several MiniFASNet models."""

    def __init__(self, specs: Sequence[AntiSpoofModelSpec], providers: Sequence[str]) -> None:
        if not specs:
            raise ValueError("At least one anti-spoofing model is required")
        available = set(ort.get_available_providers())
        selected = [p for p in providers if p in available] or ["CPUExecutionProvider"]
        self._models = [_OnnxModel(spec, selected) for spec in specs]
        self._total_weight = sum(m.spec.weight for m in self._models)
        # ONNX Runtime sessions are thread-safe for run(), the lock only bounds CPU usage
        self._lock = threading.Lock()
        logger.info(
            "Loaded %d anti-spoofing model(s) with providers %s", len(self._models), selected
        )

    def score(self, image: np.ndarray, face: FaceDetection) -> float:
        with self._lock:
            weighted = sum(m.spec.weight * m.live_probability(image, face) for m in self._models)
        return weighted / self._total_weight
