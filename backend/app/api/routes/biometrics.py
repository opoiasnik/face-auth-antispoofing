from __future__ import annotations

import time

from fastapi import APIRouter, Depends

from app.api.deps import ContainerDep, EngineDep, rate_limit
from app.biometrics.image import decode_base64_image
from app.schemas.biometrics import (
    CaptureParameters,
    ChallengeRequest,
    ChallengeResponse,
    QualityCheckRequest,
    QualityCheckResponse,
)

router = APIRouter(tags=["biometrics"])


@router.post(
    "/challenges",
    response_model=ChallengeResponse,
    status_code=201,
    dependencies=[Depends(rate_limit("challenge"))],
)
def create_challenge(body: ChallengeRequest, container: ContainerDep) -> ChallengeResponse:
    """Issue a single-use liveness challenge (random head-movement sequence)."""
    challenge = container.challenges.issue(body.purpose)
    cfg = container.challenges.settings
    return ChallengeResponse(
        challenge_id=challenge.id,
        purpose=challenge.purpose,
        actions=list(challenge.actions),
        expires_in=max(int(challenge.expires_at - time.time()), 0),
        capture=CaptureParameters(
            frames_per_step=cfg.frames_per_step,
            step_duration_ms=cfg.step_duration_ms,
            lead_in_ms=cfg.lead_in_ms,
        ),
    )


@router.post(
    "/biometrics/quality",
    response_model=QualityCheckResponse,
    dependencies=[Depends(rate_limit("quality", per_minute=120))],
)
def quality_check(
    body: QualityCheckRequest, container: ContainerDep, engine: EngineDep
) -> QualityCheckResponse:
    """Lightweight pre-flight check used by the UI to guide the user before capture."""
    image = decode_base64_image(
        body.image,
        max_bytes=container.settings.security.max_frame_bytes,
        max_side=container.settings.detection.max_image_side,
    )
    report = engine.check_quality(image)
    return QualityCheckResponse(
        ok=report.ok,
        issues=list(report.issues),
        face_size=round(report.face_size, 1),
        sharpness=round(report.sharpness, 1),
        brightness=round(report.brightness, 1),
    )
