"""FastAPI dependencies."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.biometrics.engine import BiometricEngine
from app.container import Container
from app.core.errors import (
    ForbiddenError,
    ServiceUnavailableError,
    TooManyRequestsError,
    UnauthorizedError,
)
from app.db.models import User
from app.repositories.users import UserRepository
from app.services.biometric_auth import BiometricAuthService, ClientContext

_bearer = HTTPBearer(auto_error=False)


def get_container(request: Request) -> Container:
    container: Container = request.app.state.container
    return container


ContainerDep = Annotated[Container, Depends(get_container)]


def get_db(container: ContainerDep) -> Iterator[Session]:
    session = container.session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


DbDep = Annotated[Session, Depends(get_db)]


def get_biometric_engine(container: ContainerDep) -> BiometricEngine:
    if container.biometrics is None:
        raise ServiceUnavailableError(
            "Biometric models are not loaded", details={"cause": container.biometrics_error}
        )
    return container.biometrics


EngineDep = Annotated[BiometricEngine, Depends(get_biometric_engine)]


def client_context(request: Request) -> ClientContext:
    return ClientContext(
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


ClientDep = Annotated[ClientContext, Depends(client_context)]


def get_auth_service(container: ContainerDep, db: DbDep, engine: EngineDep) -> BiometricAuthService:
    return BiometricAuthService(
        db=db,
        engine=engine,
        challenges=container.challenges,
        cipher=container.cipher,
        audit=container.audit,
        settings=container.settings,
    )


AuthServiceDep = Annotated[BiometricAuthService, Depends(get_auth_service)]


def rate_limit(scope: str, per_minute: int | None = None) -> Callable[..., None]:
    """Per-client-IP fixed-window limit for the given endpoint scope."""

    def dependency(container: ContainerDep, ctx: ClientDep) -> None:
        limit = per_minute or container.settings.security.rate_limit_per_minute
        if not container.rate_limiter.hit(f"{scope}:{ctx.ip}", limit, 60):
            raise TooManyRequestsError("Rate limit exceeded, try again later")

    return dependency


def get_current_user(
    container: ContainerDep,
    db: DbDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise UnauthorizedError("Missing bearer token")
    claims = container.tokens.decode(credentials.credentials)
    user = UserRepository(db).get(claims.user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError("User no longer active")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_admin(user: CurrentUser) -> User:
    if not user.is_admin:
        raise ForbiddenError("Administrator role required")
    return user


AdminUser = Annotated[User, Depends(require_admin)]
