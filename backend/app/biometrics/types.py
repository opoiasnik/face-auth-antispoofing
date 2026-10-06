"""Value objects shared by the biometric components."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

import numpy as np


@dataclass(frozen=True, slots=True)
class FaceDetection:
    """A detected face.

    ``landmarks`` is a (5, 2) array in image coordinates in YuNet order:
    right eye, left eye, nose tip, right mouth corner, left mouth corner
    (from the subject's point of view). ``raw`` is the original 15-value
    detector row required by the SFace alignment routine.
    """

    bbox: tuple[float, float, float, float]  # x, y, width, height
    landmarks: np.ndarray
    score: float
    raw: np.ndarray

    @property
    def area(self) -> float:
        return max(self.bbox[2], 0.0) * max(self.bbox[3], 0.0)

    @property
    def min_side(self) -> float:
        return min(self.bbox[2], self.bbox[3])

    @classmethod
    def from_yunet(cls, row: np.ndarray) -> FaceDetection:
        row = np.asarray(row, dtype=np.float32)
        return cls(
            bbox=(float(row[0]), float(row[1]), float(row[2]), float(row[3])),
            landmarks=row[4:14].reshape(5, 2).copy(),
            score=float(row[14]),
            raw=row.copy(),
        )


class QualityIssue(StrEnum):
    NO_FACE = "no_face"
    MULTIPLE_FACES = "multiple_faces"
    FACE_TOO_SMALL = "face_too_small"
    TOO_BLURRY = "too_blurry"
    TOO_DARK = "too_dark"
    TOO_BRIGHT = "too_bright"


@dataclass(frozen=True, slots=True)
class QualityReport:
    issues: tuple[QualityIssue, ...]
    face_size: float = 0.0
    sharpness: float = 0.0
    brightness: float = 0.0

    @property
    def ok(self) -> bool:
        return not self.issues


@dataclass(frozen=True, slots=True)
class HeadPose:
    """Geometric head-pose proxies computed from the 5 facial landmarks.

    ``yaw``   – horizontal nose offset from the eye midpoint, normalised by the
                inter-ocular distance. Positive values mean the subject turned
                to *their* left (nose moves to the right of a non-mirrored frame).
    ``pitch`` – vertical position of the nose between the eye line (0) and the
                mouth line (1). Looking up decreases it, looking down increases it.
    """

    yaw: float
    pitch: float


class ChallengeAction(StrEnum):
    CENTER = "center"
    TURN_LEFT = "turn_left"
    TURN_RIGHT = "turn_right"
    LOOK_UP = "look_up"
    LOOK_DOWN = "look_down"


class RejectionReason(StrEnum):
    QUALITY = "quality"
    PASSIVE_SPOOF = "passive_spoof"
    ACTIVE_CHALLENGE_FAILED = "active_challenge_failed"
    IDENTITY_INCONSISTENT = "identity_inconsistent"
    NO_MATCH = "no_match"
    DUPLICATE_FACE = "duplicate_face"


@dataclass(slots=True)
class FrameAnalysis:
    step: int
    quality: QualityReport
    face: FaceDetection | None = None
    pose: HeadPose | None = None
    liveness_score: float | None = None
    embedding: np.ndarray | None = None

    @property
    def usable(self) -> bool:
        return self.quality.ok and self.face is not None


@dataclass(frozen=True, slots=True)
class StepResult:
    step: int
    action: ChallengeAction
    passed: bool
    usable_frames: int
    peak_delta: float


@dataclass(frozen=True, slots=True)
class ActiveLivenessResult:
    passed: bool
    steps: tuple[StepResult, ...]


@dataclass(slots=True)
class SessionResult:
    """Outcome of analysing a full challenge session (all captured frames)."""

    frames: list[FrameAnalysis]
    passive_score: float | None
    active: ActiveLivenessResult | None
    consistency: float | None
    template: np.ndarray | None
    rejection: RejectionReason | None = None
    quality_issues: dict[str, int] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.rejection is None

    def summary(self) -> dict[str, object]:
        return {
            "passive_liveness": None
            if self.passive_score is None
            else round(self.passive_score, 4),
            "active_liveness": None
            if self.active is None
            else {
                "passed": self.active.passed,
                "steps": [
                    {
                        "action": s.action.value,
                        "passed": s.passed,
                        "usable_frames": s.usable_frames,
                        "peak_delta": round(s.peak_delta, 4),
                    }
                    for s in self.active.steps
                ],
            },
            "consistency": None if self.consistency is None else round(self.consistency, 4),
            "quality_issues": self.quality_issues,
        }
