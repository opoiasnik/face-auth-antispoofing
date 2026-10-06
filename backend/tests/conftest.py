from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.biometrics.factory import build_engine
from app.biometrics.types import ChallengeAction
from app.container import Container, build_container
from app.core.config import QualitySettings, SecuritySettings, Settings
from app.main import create_app
from tests.fakes import FakeDetector, FakeEmbedder, FakeLiveness, encode, make_frame


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        environment="test",
        database_url=f"sqlite:///{(tmp_path / 'test.db').as_posix()}",
        quality=QualitySettings(
            min_face_size=0, min_sharpness=0, min_brightness=0, max_brightness=255
        ),
        security=SecuritySettings(lockout_max_failures=3, rate_limit_per_minute=1000),
    )


@pytest.fixture
def container(settings: Settings) -> Container:
    engine = build_engine(
        settings,
        detector=FakeDetector(),
        embedder=FakeEmbedder(),
        passive_liveness=FakeLiveness(),
    )
    return build_container(settings, biometrics=engine)


@pytest.fixture
def client(settings: Settings, container: Container) -> Iterator[TestClient]:
    with TestClient(create_app(settings, container)) as test_client:
        yield test_client


def build_frames(
    actions: list[str],
    *,
    identity: int = 1,
    live: bool = True,
    per_step: int = 5,
    override: dict[int, ChallengeAction] | None = None,
) -> list[dict[str, Any]]:
    """Frames that perform the challenge (``override`` replaces the action of given steps)."""
    frames = []
    for step, action in enumerate(actions):
        performed = (override or {}).get(step, ChallengeAction(action))
        image = encode(make_frame(identity, performed, live))
        frames.extend({"step": step, "image": image} for _ in range(per_step))
    return frames


def new_challenge(client: TestClient, purpose: str) -> dict[str, Any]:
    response = client.post("/api/v1/challenges", json={"purpose": purpose})
    assert response.status_code == 201, response.text
    return response.json()  # type: ignore[no-any-return]


def enroll(client: TestClient, username: str, identity: int) -> dict[str, Any]:
    challenge = new_challenge(client, "enroll")
    response = client.post(
        "/api/v1/enrollment",
        json={
            "username": username,
            "full_name": username.title(),
            "challenge_id": challenge["challenge_id"],
            "frames": build_frames(challenge["actions"], identity=identity),
        },
    )
    assert response.status_code == 201, response.text
    return response.json()  # type: ignore[no-any-return]
