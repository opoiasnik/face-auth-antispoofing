from __future__ import annotations

from fastapi.testclient import TestClient

from app.biometrics.types import ChallengeAction
from app.container import Container
from app.repositories.users import UserRepository
from tests.conftest import build_frames, enroll, new_challenge
from tests.fakes import encode, make_empty_frame


def _verify(client: TestClient, username: str, **frame_kwargs):  # type: ignore[no-untyped-def]
    challenge = new_challenge(client, "authenticate")
    return client.post(
        "/api/v1/auth/verify",
        json={
            "username": username,
            "challenge_id": challenge["challenge_id"],
            "frames": build_frames(challenge["actions"], **frame_kwargs),
        },
    )


def _error(response) -> dict:  # type: ignore[no-untyped-def]
    return response.json()["error"]  # type: ignore[no-any-return]


def test_health(client: TestClient) -> None:
    assert client.get("/health/live").json() == {"status": "ok"}
    ready = client.get("/health/ready")
    assert ready.status_code == 200
    assert ready.json()["checks"] == {"database": "ok", "models": "ok"}


def test_challenge_structure(client: TestClient) -> None:
    challenge = new_challenge(client, "enroll")
    assert challenge["actions"][0] == "center"
    assert len(challenge["actions"]) == 3
    assert len(set(challenge["actions"][1:])) == 2
    assert challenge["capture"]["frames_per_step"] == 5


def test_enroll_then_verify(client: TestClient) -> None:
    enrolled = enroll(client, "alice", identity=1)
    assert enrolled["user"]["username"] == "alice"
    assert enrolled["access_token"]

    response = _verify(client, "alice", identity=1)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["match_score"] > 0.99
    assert body["liveness"]["active_liveness"]["passed"] is True


def test_username_is_normalised(client: TestClient) -> None:
    enroll(client, "  Bob.Smith ", identity=2)
    assert _verify(client, "bob.smith", identity=2).status_code == 200


def test_verify_rejects_impostor(client: TestClient) -> None:
    enroll(client, "alice", identity=1)
    response = _verify(client, "alice", identity=2)
    assert response.status_code == 401
    assert _error(response)["details"]["reason"] == "no_match"


def test_verify_unknown_user_is_indistinguishable(client: TestClient) -> None:
    response = _verify(client, "ghost", identity=1)
    assert response.status_code == 401
    assert _error(response)["details"]["reason"] == "no_match"


def test_passive_spoof_is_rejected(client: TestClient) -> None:
    enroll(client, "alice", identity=1)
    response = _verify(client, "alice", identity=1, live=False)
    assert response.status_code == 401
    assert _error(response)["details"]["reason"] == "passive_spoof"


def test_static_photo_fails_active_challenge(client: TestClient) -> None:
    enroll(client, "alice", identity=1)
    # a printed photo stays frontal during every step
    response = _verify(
        client, "alice", identity=1, override={1: ChallengeAction.CENTER, 2: ChallengeAction.CENTER}
    )
    assert response.status_code == 401
    assert _error(response)["details"]["reason"] == "active_challenge_failed"


def test_face_swap_during_session_is_rejected(client: TestClient) -> None:
    enroll(client, "alice", identity=1)
    challenge = new_challenge(client, "authenticate")
    frames = build_frames(challenge["actions"], identity=1)
    frames[-1] = build_frames(challenge["actions"], identity=7)[-1]
    response = client.post(
        "/api/v1/auth/verify",
        json={"username": "alice", "challenge_id": challenge["challenge_id"], "frames": frames},
    )
    assert response.status_code == 401
    assert _error(response)["details"]["reason"] == "identity_inconsistent"


def test_no_face_reports_quality(client: TestClient) -> None:
    challenge = new_challenge(client, "enroll")
    empty = encode(make_empty_frame())
    frames = [{"step": s, "image": empty} for s in range(len(challenge["actions"]))]
    response = client.post(
        "/api/v1/enrollment",
        json={"username": "carol", "challenge_id": challenge["challenge_id"], "frames": frames},
    )
    assert response.status_code == 401
    error = _error(response)
    assert error["details"]["reason"] == "quality"
    assert error["details"]["quality_issues"] == {"no_face": 3}


def test_challenge_is_single_use(client: TestClient) -> None:
    enroll(client, "alice", identity=1)
    challenge = new_challenge(client, "authenticate")
    payload = {
        "username": "alice",
        "challenge_id": challenge["challenge_id"],
        "frames": build_frames(challenge["actions"], identity=1),
    }
    assert client.post("/api/v1/auth/verify", json=payload).status_code == 200
    replay = client.post("/api/v1/auth/verify", json=payload)
    assert replay.status_code == 400
    assert _error(replay)["code"] == "invalid_challenge"


def test_challenge_purpose_is_enforced(client: TestClient) -> None:
    challenge = new_challenge(client, "authenticate")
    response = client.post(
        "/api/v1/enrollment",
        json={
            "username": "dave",
            "challenge_id": challenge["challenge_id"],
            "frames": build_frames(challenge["actions"]),
        },
    )
    assert response.status_code == 400


def test_missing_step_is_rejected(client: TestClient) -> None:
    challenge = new_challenge(client, "enroll")
    frames = [f for f in build_frames(challenge["actions"]) if f["step"] != 2]
    response = client.post(
        "/api/v1/enrollment",
        json={"username": "erin", "challenge_id": challenge["challenge_id"], "frames": frames},
    )
    assert response.status_code == 400


def test_duplicate_username_and_face(client: TestClient) -> None:
    enroll(client, "alice", identity=1)
    for username, identity, reason in (("alice", 3, None), ("alice2", 1, "duplicate_face")):
        challenge = new_challenge(client, "enroll")
        response = client.post(
            "/api/v1/enrollment",
            json={
                "username": username,
                "challenge_id": challenge["challenge_id"],
                "frames": build_frames(challenge["actions"], identity=identity),
            },
        )
        assert response.status_code == 409
        if reason:
            assert _error(response)["details"]["reason"] == reason


def test_identify(client: TestClient) -> None:
    enroll(client, "alice", identity=1)
    enroll(client, "bob", identity=2)
    challenge = new_challenge(client, "authenticate")
    response = client.post(
        "/api/v1/auth/identify",
        json={
            "challenge_id": challenge["challenge_id"],
            "frames": build_frames(challenge["actions"], identity=2),
        },
    )
    assert response.status_code == 200
    assert response.json()["user"]["username"] == "bob"


def test_lockout_after_repeated_failures(client: TestClient) -> None:
    enroll(client, "alice", identity=1)
    for _ in range(3):
        assert _verify(client, "alice", identity=9).status_code == 401
    locked = _verify(client, "alice", identity=1)
    assert locked.status_code == 429


def test_account_endpoints(client: TestClient) -> None:
    token = enroll(client, "alice", identity=1)["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    _verify(client, "alice", identity=5)  # failed attempt is attributed to alice

    assert client.get("/api/v1/users/me").status_code == 401
    assert client.get("/api/v1/users/me", headers=headers).json()["username"] == "alice"
    attempts = client.get("/api/v1/users/me/attempts", headers=headers).json()
    assert [a["success"] for a in attempts] == [False, True]
    assert attempts[0]["failure_reason"] == "no_match"

    assert client.delete("/api/v1/users/me", headers=headers).status_code == 204
    assert client.get("/api/v1/users/me", headers=headers).status_code == 401
    assert _verify(client, "alice", identity=1).status_code == 401


def test_reenroll_requires_same_person(client: TestClient) -> None:
    token = enroll(client, "alice", identity=1)["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    for identity, expected in ((4, 401), (1, 200)):
        challenge = new_challenge(client, "enroll")
        response = client.put(
            "/api/v1/users/me/face",
            headers=headers,
            json={
                "challenge_id": challenge["challenge_id"],
                "frames": build_frames(challenge["actions"], identity=identity),
            },
        )
        assert response.status_code == expected, response.text


def test_admin_endpoints_require_role(client: TestClient, container: Container) -> None:
    token = enroll(client, "alice", identity=1)["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/api/v1/admin/stats", headers=headers).status_code == 403

    with container.session_factory() as session, session.begin():
        user = UserRepository(session).get_by_username("alice")
        assert user is not None
        user.is_admin = True

    stats = client.get("/api/v1/admin/stats", headers=headers)
    assert stats.status_code == 200
    assert stats.json()["users"] == 1
    assert client.get("/api/v1/admin/attempts", headers=headers).status_code == 200


def test_invalid_image_payload(client: TestClient) -> None:
    challenge = new_challenge(client, "enroll")
    frames = [{"step": s, "image": "not-base64-data!!"} for s in range(3)]
    response = client.post(
        "/api/v1/enrollment",
        json={"username": "frank", "challenge_id": challenge["challenge_id"], "frames": frames},
    )
    assert response.status_code == 422
    assert _error(response)["code"] == "invalid_image"


def test_quality_endpoint(client: TestClient) -> None:
    ok = client.post("/api/v1/biometrics/quality", json={"image": encode(make_empty_frame())})
    assert ok.status_code == 200
    assert ok.json()["issues"] == ["no_face"]
