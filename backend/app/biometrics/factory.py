"""Builds a :class:`BiometricEngine` from application settings."""

from __future__ import annotations

from app.biometrics.detector import FaceDetector, YuNetDetector
from app.biometrics.embedder import FaceEmbedder, SFaceEmbedder
from app.biometrics.engine import BiometricEngine, SessionPolicy
from app.biometrics.liveness.active import ActiveLivenessConfig, ActiveLivenessVerifier
from app.biometrics.liveness.passive import (
    AntiSpoofModelSpec,
    MiniFASNetEnsemble,
    PassiveLivenessDetector,
)
from app.biometrics.quality import QualityAssessor, QualityConfig
from app.core.config import Settings


def build_quality_assessor(settings: Settings) -> QualityAssessor:
    q = settings.quality
    return QualityAssessor(
        QualityConfig(
            min_face_size=q.min_face_size,
            min_sharpness=q.min_sharpness,
            min_brightness=q.min_brightness,
            max_brightness=q.max_brightness,
            secondary_face_area_ratio=q.secondary_face_area_ratio,
        )
    )


def build_active_verifier(settings: Settings) -> ActiveLivenessVerifier:
    a = settings.active_liveness
    return ActiveLivenessVerifier(
        ActiveLivenessConfig(
            center_max_yaw=a.center_max_yaw,
            yaw_threshold=a.yaw_threshold,
            pitch_threshold=a.pitch_threshold,
            min_frames_over_threshold=a.min_frames_over_threshold,
            min_face_ratio=a.min_face_ratio,
        )
    )


def build_detector(settings: Settings) -> YuNetDetector:
    return YuNetDetector(
        settings.models.directory / settings.models.detector,
        score_threshold=settings.detection.score_threshold,
        nms_threshold=settings.detection.nms_threshold,
    )


def build_embedder(settings: Settings) -> SFaceEmbedder:
    return SFaceEmbedder(settings.models.directory / settings.models.recognizer)


def build_passive_liveness(settings: Settings) -> MiniFASNetEnsemble:
    specs = [
        AntiSpoofModelSpec(
            path=settings.models.directory / m.file, crop_scale=m.crop_scale, weight=m.weight
        )
        for m in settings.models.anti_spoof
    ]
    return MiniFASNetEnsemble(specs, settings.models.onnx_providers)


def build_engine(
    settings: Settings,
    *,
    detector: FaceDetector | None = None,
    embedder: FaceEmbedder | None = None,
    passive_liveness: PassiveLivenessDetector | None = None,
) -> BiometricEngine:
    """Create the engine; individual components may be injected (tests, experiments)."""
    return BiometricEngine(
        detector=detector or build_detector(settings),
        embedder=embedder or build_embedder(settings),
        passive_liveness=passive_liveness or build_passive_liveness(settings),
        quality=build_quality_assessor(settings),
        active_liveness=build_active_verifier(settings),
        policy=SessionPolicy(
            passive_threshold=settings.passive_liveness.threshold,
            passive_min_frame_score=settings.passive_liveness.min_frame_score,
            consistency_threshold=settings.matching.consistency_threshold,
        ),
        recognizer_version=settings.models.recognizer_version,
    )
