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
    challenge = container.challenges.issue(body.purpose)
    cfg = container.challenges.settings
    return ChallengeResponse(
        challenge_id=challenge.id,
        purpose=challenge.purpose,
        actions=list(challenge.actions),
        expires_in=max(int(challenge.expires_at - time.time()), 0),
        capture=CaptureParameters(
            center_duration_ms=cfg.center_duration_ms,
            frame_interval_ms=cfg.frame_interval_ms,
            action_timeout_ms=cfg.action_timeout_ms,
            hold_after_detection_ms=cfg.hold_after_detection_ms,
            max_frames_per_step=cfg.max_frames_per_step,
            yaw_threshold=container.settings.active_liveness.yaw_threshold,
            pitch_threshold=container.settings.active_liveness.pitch_threshold,
        ),
    )


@router.post(
    "/biometrics/quality",
    response_model=QualityCheckResponse,
    dependencies=[Depends(rate_limit("quality", per_minute=300))],
)
def quality_check(
    body: QualityCheckRequest, container: ContainerDep, engine: EngineDep
) -> QualityCheckResponse:
    image = decode_base64_image(
        body.image,
        max_bytes=container.settings.security.max_frame_bytes,
        max_side=container.settings.detection.max_image_side,
    )
    report, pose = engine.inspect(image)
    return QualityCheckResponse(
        ok=report.ok,
        issues=list(report.issues),
        face_size=round(report.face_size, 1),
        sharpness=round(report.sharpness, 1),
        brightness=round(report.brightness, 1),
        yaw=None if pose is None else round(pose.yaw, 3),
        pitch=None if pose is None else round(pose.pitch, 3),
    )
