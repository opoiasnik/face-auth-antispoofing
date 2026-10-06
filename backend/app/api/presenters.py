"""Mapping between service results and API schemas."""

from __future__ import annotations

from app.container import Container
from app.schemas.auth import AuthResponse, UserOut
from app.schemas.biometrics import CapturePayload
from app.services.biometric_auth import AuthOutcome, CaptureSubmission


def to_submission(payload: CapturePayload) -> CaptureSubmission:
    return CaptureSubmission(
        challenge_id=payload.challenge_id,
        frames=[(f.step, f.image) for f in payload.frames],
    )


def to_auth_response(container: Container, outcome: AuthOutcome) -> AuthResponse:
    user = outcome.user
    expose = container.settings.security.expose_scores
    return AuthResponse(
        access_token=container.tokens.issue(
            user_id=user.id, username=user.username, is_admin=user.is_admin
        ),
        expires_in=container.tokens.ttl_seconds,
        user=UserOut.model_validate(user),
        match_score=round(outcome.match_score, 4)
        if expose and outcome.match_score is not None
        else None,
        liveness=outcome.session.summary() if expose else None,
    )
