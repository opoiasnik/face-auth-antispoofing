from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import AuthServiceDep, ClientDep, ContainerDep, rate_limit
from app.api.presenters import to_auth_response, to_submission
from app.schemas.auth import AuthResponse, EnrollRequest, IdentifyRequest, VerifyRequest

router = APIRouter(tags=["authentication"])


@router.post(
    "/enrollment",
    response_model=AuthResponse,
    status_code=201,
    dependencies=[Depends(rate_limit("enroll", per_minute=10))],
)
def enroll(
    body: EnrollRequest, service: AuthServiceDep, container: ContainerDep, ctx: ClientDep
) -> AuthResponse:
    """Create a user and their face template after a successful liveness session."""
    outcome = service.enroll(body.username, body.full_name, to_submission(body), ctx)
    return to_auth_response(container, outcome)


@router.post(
    "/auth/verify",
    response_model=AuthResponse,
    dependencies=[Depends(rate_limit("auth"))],
)
def verify(
    body: VerifyRequest, service: AuthServiceDep, container: ContainerDep, ctx: ClientDep
) -> AuthResponse:
    """1:1 verification – the user claims an identity (username) and proves it by face."""
    outcome = service.verify(body.username, to_submission(body), ctx)
    return to_auth_response(container, outcome)


@router.post(
    "/auth/identify",
    response_model=AuthResponse,
    dependencies=[Depends(rate_limit("auth"))],
)
def identify(
    body: IdentifyRequest, service: AuthServiceDep, container: ContainerDep, ctx: ClientDep
) -> AuthResponse:
    """1:N identification – passwordless login by face only."""
    outcome = service.identify(to_submission(body), ctx)
    return to_auth_response(container, outcome)
