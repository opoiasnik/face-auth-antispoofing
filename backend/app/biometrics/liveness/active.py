"""Active liveness: verification of a randomised head-movement challenge.

The challenge always starts with a ``center`` step that establishes the
subject's personal neutral pose. Every following step must show a movement in
the requested direction relative to that baseline. Because the order of the
actions is random and the challenge is single-use, a pre-recorded video or a
static photo cannot satisfy it.
"""

from __future__ import annotations

import secrets
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from app.biometrics.types import (
    ActiveLivenessResult,
    ChallengeAction,
    HeadPose,
    StepResult,
)


@dataclass(frozen=True, slots=True)
class ActiveLivenessConfig:
    center_max_yaw: float
    yaw_threshold: float
    pitch_threshold: float
    min_frames_over_threshold: int
    min_face_ratio: float


def generate_actions(pool: Sequence[ChallengeAction], steps: int) -> list[ChallengeAction]:
    """Random (CSPRNG) sequence: ``center`` followed by ``steps`` distinct actions."""
    candidates = list(dict.fromkeys(pool))
    if steps > len(candidates):
        raise ValueError("Not enough distinct actions for the requested number of steps")
    rng = secrets.SystemRandom()
    return [ChallengeAction.CENTER, *rng.sample(candidates, steps)]


def _movement(action: ChallengeAction, pose: HeadPose, baseline: HeadPose) -> float:
    """Signed movement towards the requested direction (positive = correct direction)."""
    match action:
        case ChallengeAction.TURN_LEFT:
            return pose.yaw - baseline.yaw
        case ChallengeAction.TURN_RIGHT:
            return baseline.yaw - pose.yaw
        case ChallengeAction.LOOK_UP:
            return baseline.pitch - pose.pitch
        case ChallengeAction.LOOK_DOWN:
            return pose.pitch - baseline.pitch
        case _:
            return 0.0


class ActiveLivenessVerifier:
    def __init__(self, config: ActiveLivenessConfig) -> None:
        self._config = config

    def _threshold(self, action: ChallengeAction) -> float:
        if action in (ChallengeAction.TURN_LEFT, ChallengeAction.TURN_RIGHT):
            return self._config.yaw_threshold
        return self._config.pitch_threshold

    def verify(
        self,
        actions: Sequence[ChallengeAction],
        poses_per_step: Sequence[Sequence[HeadPose]],
        frames_per_step: Sequence[int],
    ) -> ActiveLivenessResult:
        """Evaluate each step.

        ``poses_per_step[i]`` holds poses of usable frames of step ``i`` and
        ``frames_per_step[i]`` the number of frames submitted for that step.
        """
        if not actions or actions[0] is not ChallengeAction.CENTER:
            raise ValueError("Challenge must start with the center step")
        cfg = self._config
        results: list[StepResult] = []

        def enough_faces(step: int) -> bool:
            submitted = frames_per_step[step]
            return submitted > 0 and len(poses_per_step[step]) / submitted >= cfg.min_face_ratio

        center = poses_per_step[0]
        if not center or not enough_faces(0):
            return ActiveLivenessResult(
                passed=False,
                steps=(StepResult(0, ChallengeAction.CENTER, False, len(center), 0.0),),
            )
        baseline = HeadPose(
            yaw=float(np.median([p.yaw for p in center])),
            pitch=float(np.median([p.pitch for p in center])),
        )
        center_ok = abs(baseline.yaw) <= cfg.center_max_yaw
        results.append(StepResult(0, ChallengeAction.CENTER, center_ok, len(center), baseline.yaw))

        for step, action in enumerate(actions[1:], start=1):
            poses = poses_per_step[step]
            movements = [_movement(action, pose, baseline) for pose in poses]
            peak = max(movements, default=0.0)
            over = sum(m >= self._threshold(action) for m in movements)
            passed = enough_faces(step) and over >= cfg.min_frames_over_threshold
            results.append(StepResult(step, action, passed, len(poses), peak))

        return ActiveLivenessResult(passed=all(r.passed for r in results), steps=tuple(results))
