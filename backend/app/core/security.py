"""Access tokens (JWT) and encryption of biometric templates at rest."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt
import numpy as np
from cryptography.fernet import Fernet, InvalidToken

from app.core.errors import UnauthorizedError


@dataclass(frozen=True, slots=True)
class TokenClaims:
    user_id: int
    username: str
    is_admin: bool
    expires_at: datetime


class TokenService:
    def __init__(self, secret: str, algorithm: str, ttl_minutes: int) -> None:
        self._secret = secret
        self._algorithm = algorithm
        self._ttl = timedelta(minutes=ttl_minutes)

    @property
    def ttl_seconds(self) -> int:
        return int(self._ttl.total_seconds())

    def issue(self, *, user_id: int, username: str, is_admin: bool) -> str:
        now = datetime.now(UTC)
        payload = {
            "sub": str(user_id),
            "username": username,
            "adm": is_admin,
            "iat": now,
            "exp": now + self._ttl,
            "jti": uuid.uuid4().hex,
            "typ": "access",
        }
        return jwt.encode(payload, self._secret, algorithm=self._algorithm)

    def decode(self, token: str) -> TokenClaims:
        try:
            payload = jwt.decode(
                token,
                self._secret,
                algorithms=[self._algorithm],
                options={"require": ["sub", "exp", "iat", "typ"]},
            )
        except jwt.ExpiredSignatureError as exc:
            raise UnauthorizedError("Token expired") from exc
        except jwt.PyJWTError as exc:
            raise UnauthorizedError("Invalid token") from exc
        if payload.get("typ") != "access":
            raise UnauthorizedError("Invalid token type")
        return TokenClaims(
            user_id=int(payload["sub"]),
            username=str(payload.get("username", "")),
            is_admin=bool(payload.get("adm", False)),
            expires_at=datetime.fromtimestamp(payload["exp"], UTC),
        )


class TemplateCipher:
    """Symmetric authenticated encryption (Fernet: AES-128-CBC + HMAC-SHA256) of embeddings."""

    def __init__(self, key: bytes) -> None:
        self._fernet = Fernet(key)

    def encrypt(self, embedding: np.ndarray) -> bytes:
        return self._fernet.encrypt(np.asarray(embedding, dtype=np.float32).tobytes())

    def decrypt(self, token: bytes) -> np.ndarray:
        try:
            raw = self._fernet.decrypt(token)
        except InvalidToken as exc:
            raise ValueError("Template cannot be decrypted with the configured key") from exc
        return np.frombuffer(raw, dtype=np.float32).copy()
