from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, StringConstraints

from app.schemas.biometrics import CapturePayload


def _normalise_username(value: object) -> object:
    return value.strip().lower() if isinstance(value, str) else value


Username = Annotated[
    str,
    BeforeValidator(_normalise_username),
    StringConstraints(pattern=r"^[a-z0-9._-]{3,32}$"),
]


class EnrollRequest(CapturePayload):
    username: Username
    full_name: Annotated[str | None, Field(max_length=128)] = None


class VerifyRequest(CapturePayload):
    username: Username


class IdentifyRequest(CapturePayload):
    pass


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    full_name: str | None
    is_admin: bool
    is_active: bool
    created_at: datetime


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut
    match_score: float | None = None
    liveness: dict[str, object] | None = None


class AttemptOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int | None
    username: str | None
    mode: str
    success: bool
    failure_reason: str | None
    match_score: float | None
    passive_score: float | None
    active_passed: bool | None
    frames: int
    duration_ms: int
    client_ip: str | None
    created_at: datetime


class StatsBucket(BaseModel):
    mode: str
    success: bool
    failure_reason: str | None
    count: int


class StatsOut(BaseModel):
    users: int
    attempts: list[StatsBucket]
