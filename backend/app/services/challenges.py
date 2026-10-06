"""Single-use, short-lived liveness challenges (nonce + random action sequence)."""

from __future__ import annotations

import json
import secrets
import threading
import time
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Protocol

from app.biometrics.liveness.active import generate_actions
from app.biometrics.types import ChallengeAction
from app.core.config import ChallengeSettings
from app.core.errors import ChallengeError

if TYPE_CHECKING:
    from redis import Redis


class ChallengePurpose(StrEnum):
    ENROLL = "enroll"
    AUTHENTICATE = "authenticate"


@dataclass(frozen=True, slots=True)
class Challenge:
    id: str
    purpose: ChallengePurpose
    actions: tuple[ChallengeAction, ...]
    expires_at: float  # unix timestamp

    def to_json(self) -> str:
        return json.dumps(
            {
                "id": self.id,
                "purpose": self.purpose.value,
                "actions": [a.value for a in self.actions],
                "expires_at": self.expires_at,
            }
        )

    @classmethod
    def from_json(cls, raw: str | bytes) -> Challenge:
        data = json.loads(raw)
        return cls(
            id=data["id"],
            purpose=ChallengePurpose(data["purpose"]),
            actions=tuple(ChallengeAction(a) for a in data["actions"]),
            expires_at=float(data["expires_at"]),
        )


class ChallengeStore(Protocol):
    def save(self, challenge: Challenge, ttl_seconds: int) -> None: ...

    def pop(self, challenge_id: str) -> Challenge | None:
        """Atomically fetch and delete (guarantees single use)."""
        ...


class InMemoryChallengeStore:
    def __init__(self) -> None:
        self._items: dict[str, Challenge] = {}
        self._lock = threading.Lock()

    def save(self, challenge: Challenge, ttl_seconds: int) -> None:
        with self._lock:
            self._purge_expired()
            self._items[challenge.id] = challenge

    def pop(self, challenge_id: str) -> Challenge | None:
        with self._lock:
            return self._items.pop(challenge_id, None)

    def _purge_expired(self) -> None:
        now = time.time()
        for key in [k for k, c in self._items.items() if c.expires_at < now]:
            del self._items[key]


class RedisChallengeStore:
    def __init__(self, client: Redis, prefix: str = "fa:challenge:") -> None:
        self._client = client
        self._prefix = prefix

    def save(self, challenge: Challenge, ttl_seconds: int) -> None:
        self._client.set(self._prefix + challenge.id, challenge.to_json(), ex=ttl_seconds)

    def pop(self, challenge_id: str) -> Challenge | None:
        raw = self._client.getdel(self._prefix + challenge_id)
        return Challenge.from_json(raw) if raw else None


class ChallengeService:
    def __init__(
        self,
        store: ChallengeStore,
        settings: ChallengeSettings,
        action_pool: list[ChallengeAction],
        steps: int,
    ) -> None:
        self._store = store
        self._settings = settings
        self._pool = action_pool
        self._steps = steps

    @property
    def settings(self) -> ChallengeSettings:
        return self._settings

    def issue(self, purpose: ChallengePurpose) -> Challenge:
        challenge = Challenge(
            id=secrets.token_urlsafe(24),
            purpose=purpose,
            actions=tuple(generate_actions(self._pool, self._steps)),
            expires_at=time.time() + self._settings.ttl_seconds,
        )
        self._store.save(challenge, self._settings.ttl_seconds)
        return challenge

    def consume(self, challenge_id: str, purpose: ChallengePurpose) -> Challenge:
        challenge = self._store.pop(challenge_id)
        if challenge is None:
            raise ChallengeError("Challenge does not exist or was already used")
        if challenge.expires_at < time.time():
            raise ChallengeError("Challenge expired")
        if challenge.purpose is not purpose:
            raise ChallengeError("Challenge issued for a different purpose")
        return challenge
