from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field

from app.biometrics.types import ChallengeAction, QualityIssue
from app.services.challenges import ChallengePurpose

Base64Image = Annotated[str, Field(min_length=16, description="Base64 JPEG/PNG or data URL")]


class ChallengeRequest(BaseModel):
    purpose: ChallengePurpose


class CaptureParameters(BaseModel):
    frames_per_step: int
    step_duration_ms: int
    lead_in_ms: int


class ChallengeResponse(BaseModel):
    challenge_id: str
    purpose: ChallengePurpose
    actions: list[ChallengeAction]
    expires_in: int
    capture: CaptureParameters


class FramePayload(BaseModel):
    step: int = Field(ge=0, le=16)
    image: Base64Image


class CapturePayload(BaseModel):
    challenge_id: str = Field(min_length=8, max_length=128)
    frames: list[FramePayload] = Field(min_length=1, max_length=64)


class QualityCheckRequest(BaseModel):
    image: Base64Image


class QualityCheckResponse(BaseModel):
    ok: bool
    issues: list[QualityIssue]
    face_size: float
    sharpness: float
    brightness: float
