from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response

from app.api.deps import (
    AuthServiceDep,
    ClientDep,
    ContainerDep,
    CurrentUser,
    DbDep,
    rate_limit,
)
from app.api.presenters import to_auth_response, to_submission
from app.repositories.users import UserRepository
from app.schemas.auth import AttemptOut, AuthResponse, UserOut
from app.schemas.biometrics import CapturePayload

router = APIRouter(prefix="/users/me", tags=["account"])


@router.get("", response_model=UserOut)
def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)


@router.get("/attempts", response_model=list[AttemptOut])
def my_attempts(
    user: CurrentUser,
    container: ContainerDep,
    limit: int = Query(default=20, ge=1, le=100),
) -> list[AttemptOut]:
    attempts = container.audit.list_attempts(user_id=user.id, limit=limit)
    return [AttemptOut.model_validate(a) for a in attempts]


@router.put(
    "/face",
    response_model=AuthResponse,
    dependencies=[Depends(rate_limit("enroll", per_minute=10))],
)
def reenroll_face(
    body: CapturePayload,
    user: CurrentUser,
    service: AuthServiceDep,
    container: ContainerDep,
    ctx: ClientDep,
) -> AuthResponse:
    """Replace the stored template (e.g. after appearance change). Requires a matching face."""
    outcome = service.reenroll(user, to_submission(body), ctx)
    return to_auth_response(container, outcome)


@router.delete("", status_code=204)
def delete_me(user: CurrentUser, db: DbDep) -> Response:
    """Right to erasure (GDPR art. 17): removes the account and all biometric templates."""
    UserRepository(db).delete(user)
    return Response(status_code=204)
