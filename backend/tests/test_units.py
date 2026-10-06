from __future__ import annotations

import time

import numpy as np
import pytest
from cryptography.fernet import Fernet
from pydantic import ValidationError

from app.biometrics.embedder import TemplateMatcher, mean_template
from app.biometrics.liveness.active import (
    ActiveLivenessConfig,
    ActiveLivenessVerifier,
    generate_actions,
)
from app.biometrics.liveness.pose import estimate_head_pose
from app.biometrics.types import ChallengeAction, HeadPose
from app.core.config import ChallengeSettings, SecuritySettings, Settings
from app.core.errors import ChallengeError, UnauthorizedError
from app.core.rate_limit import InMemoryRateLimiter
from app.core.security import TemplateCipher, TokenService
from app.services.challenges import (
    Challenge,
    ChallengePurpose,
    ChallengeService,
    InMemoryChallengeStore,
)

FRONTAL = np.array([[80, 100], [120, 100], [100, 133], [85, 160], [115, 160]], dtype=float)


def _rotate(points: np.ndarray, degrees: float) -> np.ndarray:
    theta = np.radians(degrees)
    rot = np.array([[np.cos(theta), -np.sin(theta)], [np.sin(theta), np.cos(theta)]])
    center = points.mean(axis=0)
    return (points - center) @ rot.T + center


class TestHeadPose:
    def test_frontal(self) -> None:
        pose = estimate_head_pose(FRONTAL)
        assert pose.yaw == pytest.approx(0.0)
        assert pose.pitch == pytest.approx(0.55)

    def test_yaw_sign(self) -> None:
        turned = FRONTAL.copy()
        turned[2, 0] += 15  # nose to the right of a non-mirrored frame
        assert estimate_head_pose(turned).yaw > 0.3

    def test_roll_invariance(self) -> None:
        turned = FRONTAL.copy()
        turned[2, 0] += 15
        reference = estimate_head_pose(turned)
        rolled = estimate_head_pose(_rotate(turned, 25))
        assert rolled.yaw == pytest.approx(reference.yaw, abs=1e-6)
        assert rolled.pitch == pytest.approx(reference.pitch, abs=1e-6)

    def test_degenerate(self) -> None:
        with pytest.raises(ValueError):
            estimate_head_pose(np.zeros((5, 2)))


class TestActiveLiveness:
    verifier = ActiveLivenessVerifier(
        ActiveLivenessConfig(
            center_max_yaw=0.2,
            yaw_threshold=0.2,
            pitch_threshold=0.07,
            min_frames_over_threshold=2,
            min_face_ratio=0.8,
        )
    )
    actions = (ChallengeAction.CENTER, ChallengeAction.TURN_LEFT, ChallengeAction.LOOK_DOWN)

    def _run(self, left_yaw: float, down_pitch: float, faces: int = 5):  # type: ignore[no-untyped-def]
        center = [HeadPose(0.02, 0.55)] * 5
        left = [HeadPose(0.0, 0.55), *[HeadPose(left_yaw, 0.55)] * 4][:faces]
        down = [HeadPose(0.0, down_pitch)] * 5
        return self.verifier.verify(self.actions, [center, left, down], [5, 5, 5])

    def test_pass(self) -> None:
        result = self._run(0.4, 0.68)
        assert result.passed
        assert [s.passed for s in result.steps] == [True, True, True]

    def test_wrong_direction_fails(self) -> None:
        result = self._run(-0.4, 0.68)
        assert not result.passed
        assert not result.steps[1].passed

    def test_insufficient_movement_fails(self) -> None:
        assert not self._run(0.4, 0.58).passed

    def test_too_few_faces_fails(self) -> None:
        assert not self._run(0.4, 0.68, faces=3).passed

    def test_generate_actions(self) -> None:
        pool = [ChallengeAction.TURN_LEFT, ChallengeAction.TURN_RIGHT, ChallengeAction.LOOK_UP]
        seen = set()
        for _ in range(200):
            actions = generate_actions(pool, 2)
            assert actions[0] is ChallengeAction.CENTER
            assert len(set(actions[1:])) == 2
            seen.add(tuple(actions))
        assert len(seen) == 6  # all 3P2 permutations occur
        with pytest.raises(ValueError):
            generate_actions(pool, 4)


class TestMatcher:
    def test_verify_and_identify(self) -> None:
        a, b = np.eye(4, dtype=np.float32)[:2]
        matcher = TemplateMatcher(threshold=0.6)
        assert matcher.verify(a, [b, a]).matched
        assert not matcher.verify(a, [b]).matched
        assert not matcher.verify(a, []).matched
        result = matcher.identify(b, [("a", a), ("b", b)])
        assert result.key == "b" and result.matched
        assert matcher.identify(np.ones(4), [("a", a)]).key is None

    def test_mean_template_is_normalised(self) -> None:
        template = mean_template([np.array([3.0, 0.0]), np.array([0.0, 1.0])])
        assert np.linalg.norm(template) == pytest.approx(1.0)


class TestSecurity:
    def test_token_roundtrip(self) -> None:
        service = TokenService("s" * 32, "HS256", 5)
        claims = service.decode(service.issue(user_id=7, username="eve", is_admin=True))
        assert (claims.user_id, claims.username, claims.is_admin) == (7, "eve", True)

    def test_token_tampering(self) -> None:
        token = TokenService("s" * 32, "HS256", 5).issue(user_id=1, username="x", is_admin=False)
        with pytest.raises(UnauthorizedError):
            TokenService("o" * 32, "HS256", 5).decode(token)

    def test_cipher(self) -> None:
        vector = np.random.default_rng(0).normal(size=128).astype(np.float32)
        cipher = TemplateCipher(Fernet.generate_key())
        token = cipher.encrypt(vector)
        assert vector.tobytes() not in token
        assert np.array_equal(cipher.decrypt(token), vector)
        with pytest.raises(ValueError):
            TemplateCipher(Fernet.generate_key()).decrypt(token)

    def test_production_requires_secrets(self) -> None:
        with pytest.raises(ValidationError):
            Settings(environment="production")
        Settings(
            environment="production",
            security=SecuritySettings(
                jwt_secret="x" * 40,
                template_encryption_key=Fernet.generate_key().decode(),
                expose_scores=False,
            ),
        )

    def test_rate_limiter(self) -> None:
        limiter = InMemoryRateLimiter()
        assert all(limiter.hit("k", 3, 60) for _ in range(3))
        assert not limiter.hit("k", 3, 60)
        assert limiter.hit("other", 3, 60)


class TestChallenges:
    def _service(self, ttl: int = 30) -> ChallengeService:
        return ChallengeService(
            InMemoryChallengeStore(),
            ChallengeSettings(ttl_seconds=max(ttl, 10)),
            [ChallengeAction.TURN_LEFT, ChallengeAction.TURN_RIGHT],
            2,
        )

    def test_single_use(self) -> None:
        service = self._service()
        challenge = service.issue(ChallengePurpose.ENROLL)
        assert service.consume(challenge.id, ChallengePurpose.ENROLL) == challenge
        with pytest.raises(ChallengeError):
            service.consume(challenge.id, ChallengePurpose.ENROLL)

    def test_expired(self, monkeypatch: pytest.MonkeyPatch) -> None:
        service = self._service()
        challenge = service.issue(ChallengePurpose.AUTHENTICATE)
        monkeypatch.setattr(time, "time", lambda: challenge.expires_at + 1)
        with pytest.raises(ChallengeError):
            service.consume(challenge.id, ChallengePurpose.AUTHENTICATE)

    def test_serialisation(self) -> None:
        challenge = self._service().issue(ChallengePurpose.ENROLL)
        assert Challenge.from_json(challenge.to_json()) == challenge
