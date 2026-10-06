"""Deterministic stand-ins for the neural models.

A synthetic frame carries its ground truth in the top-left pixel (B, G, R):
  * B – identity id (embedding is a one-hot vector at that index)
  * G – pose code (see ``POSE_CODES``)
  * R – 255 = live presentation, anything else = spoof
"""

from __future__ import annotations

import base64

import cv2
import numpy as np

from app.biometrics.types import ChallengeAction, FaceDetection

EMBEDDING_SIZE = 128
POSE_CODES = {
    ChallengeAction.CENTER: 0,
    ChallengeAction.TURN_LEFT: 1,
    ChallengeAction.TURN_RIGHT: 2,
    ChallengeAction.LOOK_UP: 3,
    ChallengeAction.LOOK_DOWN: 4,
}
_POSE_OFFSETS = {0: (0.0, 0.55), 1: (0.45, 0.55), 2: (-0.45, 0.55), 3: (0.0, 0.35), 4: (0.0, 0.75)}
NO_FACE_CODE = 99


def make_frame(identity: int, action: ChallengeAction, live: bool = True) -> np.ndarray:
    image = np.full((64, 64, 3), 128, dtype=np.uint8)
    image[0, 0] = (identity, POSE_CODES[action], 255 if live else 0)
    return image


def make_empty_frame() -> np.ndarray:
    image = np.full((64, 64, 3), 128, dtype=np.uint8)
    image[0, 0] = (0, NO_FACE_CODE, 255)
    return image


def encode(image: np.ndarray) -> str:
    ok, buffer = cv2.imencode(".png", image)
    assert ok
    return base64.b64encode(buffer.tobytes()).decode()


class FakeDetector:
    def detect(self, image: np.ndarray) -> list[FaceDetection]:
        _, pose_code, _ = (int(v) for v in image[0, 0])
        if pose_code == NO_FACE_CODE:
            return []
        yaw, pitch = _POSE_OFFSETS[pose_code]
        eye_y, eye_dist, face_h = 100.0, 40.0, 60.0
        landmarks = np.array(
            [
                [80.0, eye_y],
                [120.0, eye_y],
                [100.0 + yaw * eye_dist, eye_y + pitch * face_h],
                [85.0, eye_y + face_h],
                [115.0, eye_y + face_h],
            ],
            dtype=np.float32,
        )
        raw = np.concatenate([[0, 0, 200, 200], landmarks.ravel(), [0.99]]).astype(np.float32)
        return [FaceDetection.from_yunet(raw)]


class FakeEmbedder:
    def embed(self, image: np.ndarray, face: FaceDetection) -> np.ndarray:
        vector = np.zeros(EMBEDDING_SIZE, dtype=np.float32)
        vector[int(image[0, 0, 0]) % EMBEDDING_SIZE] = 1.0
        return vector


class FakeLiveness:
    def score(self, image: np.ndarray, face: FaceDetection) -> float:
        return 0.99 if int(image[0, 0, 2]) == 255 else 0.05
