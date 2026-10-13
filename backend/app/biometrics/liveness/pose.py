from __future__ import annotations

import numpy as np

from app.biometrics.types import HeadPose

_EPS = 1e-6


def estimate_head_pose(landmarks: np.ndarray) -> HeadPose:
    points = np.asarray(landmarks, dtype=np.float64).reshape(5, 2)
    eyes = points[:2]
    eye_a, eye_b = sorted(eyes, key=lambda p: p[0])
    eye_mid = (eye_a + eye_b) / 2.0

    angle = np.arctan2(eye_b[1] - eye_a[1], eye_b[0] - eye_a[0])
    cos_a, sin_a = np.cos(-angle), np.sin(-angle)
    rotation = np.array([[cos_a, -sin_a], [sin_a, cos_a]])
    aligned = (points - eye_mid) @ rotation.T

    eye_distance = float(np.linalg.norm(eye_b - eye_a))
    nose = aligned[2]
    mouth_mid = (aligned[3] + aligned[4]) / 2.0
    face_height = float(mouth_mid[1])
    if eye_distance < _EPS or face_height < _EPS:
        raise ValueError("Degenerate landmarks")

    return HeadPose(yaw=float(nose[0] / eye_distance), pitch=float(nose[1] / face_height))
