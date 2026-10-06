"""Head-pose proxies from the 5-point landmarks (roll-compensated)."""

from __future__ import annotations

import numpy as np

from app.biometrics.types import HeadPose

_EPS = 1e-6


def estimate_head_pose(landmarks: np.ndarray) -> HeadPose:
    """Estimate yaw/pitch proxies; see :class:`HeadPose` for the sign convention.

    The landmarks are first rotated so that the eye line is horizontal, which
    removes the influence of head roll (tilting the head sideways).
    """
    points = np.asarray(landmarks, dtype=np.float64).reshape(5, 2)
    eyes = points[:2]
    # order the eyes left-to-right in image space regardless of detector convention
    eye_a, eye_b = sorted(eyes, key=lambda p: p[0])
    eye_mid = (eye_a + eye_b) / 2.0

    angle = np.arctan2(eye_b[1] - eye_a[1], eye_b[0] - eye_a[0])
    cos_a, sin_a = np.cos(-angle), np.sin(-angle)
    rotation = np.array([[cos_a, -sin_a], [sin_a, cos_a]])
    aligned = (points - eye_mid) @ rotation.T

    eye_distance = float(np.linalg.norm(eye_b - eye_a))
    nose = aligned[2]
    mouth_mid = (aligned[3] + aligned[4]) / 2.0
    face_height = float(mouth_mid[1])  # eye midpoint is the origin
    if eye_distance < _EPS or face_height < _EPS:
        raise ValueError("Degenerate landmarks")

    return HeadPose(yaw=float(nose[0] / eye_distance), pitch=float(nose[1] / face_height))
