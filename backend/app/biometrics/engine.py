"""Orchestrates detection, quality, liveness and embedding for a capture session."""

from __future__ import annotations

import logging
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from app.biometrics.detector import FaceDetector
from app.biometrics.embedder import FaceEmbedder, cosine_similarity, mean_template
from app.biometrics.liveness.active import ActiveLivenessVerifier
from app.biometrics.liveness.passive import PassiveLivenessDetector
from app.biometrics.liveness.pose import estimate_head_pose
from app.biometrics.quality import QualityAssessor
from app.biometrics.types import (
    ChallengeAction,
    FrameAnalysis,
    HeadPose,
    QualityReport,
    RejectionReason,
    SessionResult,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class SessionPolicy:
    passive_threshold: float
    passive_min_frame_score: float
    consistency_threshold: float


class BiometricEngine:
    """Facade over the biometric components. Stateless and safe to share between requests."""

    def __init__(
        self,
        *,
        detector: FaceDetector,
        embedder: FaceEmbedder,
        passive_liveness: PassiveLivenessDetector,
        quality: QualityAssessor,
        active_liveness: ActiveLivenessVerifier,
        policy: SessionPolicy,
        recognizer_version: str,
    ) -> None:
        self._detector = detector
        self._embedder = embedder
        self._passive = passive_liveness
        self._quality = quality
        self._active = active_liveness
        self._policy = policy
        self.recognizer_version = recognizer_version

    # read-only access to the components (used by the evaluation tooling)
    @property
    def detector(self) -> FaceDetector:
        return self._detector

    @property
    def embedder(self) -> FaceEmbedder:
        return self._embedder

    @property
    def passive_liveness(self) -> PassiveLivenessDetector:
        return self._passive

    @property
    def quality(self) -> QualityAssessor:
        return self._quality

    # -- single frame -------------------------------------------------------------------------

    def check_quality(self, image: np.ndarray) -> QualityReport:
        return self._quality.assess(image, self._detector.detect(image))

    def analyze_frame(self, image: np.ndarray, step: int = 0) -> FrameAnalysis:
        faces = self._detector.detect(image)
        report = self._quality.assess(image, faces)
        analysis = FrameAnalysis(step=step, quality=report, face=faces[0] if faces else None)
        if not analysis.usable:
            return analysis
        assert analysis.face is not None
        try:
            analysis.pose = estimate_head_pose(analysis.face.landmarks)
        except ValueError:
            logger.debug("Degenerate landmarks in step %d", step)
        analysis.liveness_score = self._passive.score(image, analysis.face)
        analysis.embedding = self._embedder.embed(image, analysis.face)
        return analysis

    # -- session ------------------------------------------------------------------------------

    def evaluate_session(
        self, actions: Sequence[ChallengeAction], frames: Sequence[tuple[int, np.ndarray]]
    ) -> SessionResult:
        """Analyse all frames of a challenge; ``frames`` holds ``(step_index, image)`` pairs."""
        analyses = [self.analyze_frame(image, step) for step, image in frames]
        usable = [a for a in analyses if a.usable and a.embedding is not None]
        issue_counts = Counter(issue.value for a in analyses for issue in a.quality.issues)

        submitted = [0] * len(actions)
        poses: list[list[HeadPose]] = [[] for _ in actions]
        for a in analyses:
            submitted[a.step] += 1
            if a.usable and a.pose is not None:
                poses[a.step].append(a.pose)
        active = self._active.verify(actions, poses, submitted)

        live_scores = [a.liveness_score for a in usable if a.liveness_score is not None]
        passive = float(np.mean(live_scores)) if live_scores else None

        center = [a.embedding for a in usable if a.step == 0 and a.embedding is not None]
        template = mean_template(center) if center else None
        consistency = (
            min(cosine_similarity(a.embedding, template) for a in usable if a.embedding is not None)
            if template is not None
            else None
        )

        result = SessionResult(
            frames=analyses,
            passive_score=passive,
            active=active,
            consistency=consistency,
            template=template,
            quality_issues=dict(issue_counts),
        )
        result.rejection = self._decide(result, live_scores)
        return result

    def _decide(self, result: SessionResult, live_scores: list[float]) -> RejectionReason | None:
        policy = self._policy
        if result.template is None or result.passive_score is None:
            return RejectionReason.QUALITY
        if (
            result.passive_score < policy.passive_threshold
            or min(live_scores) < policy.passive_min_frame_score
        ):
            return RejectionReason.PASSIVE_SPOOF
        if result.active is None or not result.active.passed:
            return RejectionReason.ACTIVE_CHALLENGE_FAILED
        if result.consistency is None or result.consistency < policy.consistency_threshold:
            return RejectionReason.IDENTITY_INCONSISTENT
        return None
