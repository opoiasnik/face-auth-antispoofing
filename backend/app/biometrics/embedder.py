"""Face embedding extraction (OpenCV SFace) and template matching."""

from __future__ import annotations

import threading
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Generic, Protocol, TypeVar

import cv2
import numpy as np

from app.biometrics.types import FaceDetection

K = TypeVar("K")


def l2_normalize(vector: np.ndarray) -> np.ndarray:
    vector = np.asarray(vector, dtype=np.float32).ravel()
    norm = float(np.linalg.norm(vector))
    if norm == 0.0:
        raise ValueError("Cannot normalise a zero vector")
    return vector / norm


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(l2_normalize(a), l2_normalize(b)))


def mean_template(embeddings: Sequence[np.ndarray]) -> np.ndarray:
    if not embeddings:
        raise ValueError("At least one embedding is required")
    return l2_normalize(np.mean([l2_normalize(e) for e in embeddings], axis=0))


class FaceEmbedder(Protocol):
    def embed(self, image: np.ndarray, face: FaceDetection) -> np.ndarray:
        """Return an L2-normalised embedding of the aligned face."""
        ...


class SFaceEmbedder:
    """MobileFaceNet-style recogniser trained with SFace loss (Zhong et al., 2021)."""

    def __init__(self, model_path: Path) -> None:
        if not model_path.is_file():
            raise FileNotFoundError(model_path)
        self._model = cv2.FaceRecognizerSF.create(str(model_path), "")
        self._lock = threading.Lock()

    def embed(self, image: np.ndarray, face: FaceDetection) -> np.ndarray:
        with self._lock:
            aligned = self._model.alignCrop(image, face.raw)
            feature = self._model.feature(aligned)
        return l2_normalize(feature)


@dataclass(frozen=True, slots=True)
class MatchResult:
    score: float
    matched: bool


@dataclass(frozen=True, slots=True)
class IdentifyResult(Generic[K]):
    key: K | None
    score: float
    matched: bool


class TemplateMatcher:
    def __init__(self, threshold: float) -> None:
        self.threshold = threshold

    def verify(self, probe: np.ndarray, references: Sequence[np.ndarray]) -> MatchResult:
        """1:1 comparison against all templates of a single identity (best score wins)."""
        if not references:
            return MatchResult(score=-1.0, matched=False)
        score = max(cosine_similarity(probe, ref) for ref in references)
        return MatchResult(score=score, matched=score >= self.threshold)

    def identify(
        self, probe: np.ndarray, gallery: Iterable[tuple[K, np.ndarray]]
    ) -> IdentifyResult[K]:
        """1:N search; returns the best-scoring identity."""
        best_key: K | None = None
        best_score = -1.0
        for key, template in gallery:
            score = cosine_similarity(probe, template)
            if score > best_score:
                best_key, best_score = key, score
        matched = best_key is not None and best_score >= self.threshold
        return IdentifyResult(key=best_key if matched else None, score=best_score, matched=matched)
