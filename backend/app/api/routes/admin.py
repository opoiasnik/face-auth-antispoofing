from __future__ import annotations

from fastapi import APIRouter, Query, Response

from app.api.deps import AdminUser, ContainerDep, DbDep
from app.core.errors import ConflictError, NotFoundError
from app.repositories.users import UserRepository
from app.schemas.auth import AttemptOut, StatsBucket, StatsOut, UserOut

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=list[UserOut])
def list_users(
    _: AdminUser,
    db: DbDep,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[UserOut]:
    return [
        UserOut.model_validate(u) for u in UserRepository(db).list_page(offset=offset, limit=limit)
    ]


@router.patch("/users/{user_id}/active", response_model=UserOut)
def set_active(user_id: int, active: bool, admin: AdminUser, db: DbDep) -> UserOut:
    user = UserRepository(db).get(user_id)
    if user is None:
        raise NotFoundError("User not found")
    if user.id == admin.id:
        raise ConflictError("Administrators cannot deactivate themselves")
    user.is_active = active
    db.flush()
    return UserOut.model_validate(user)


@router.delete("/users/{user_id}", status_code=204)
def delete_user(user_id: int, admin: AdminUser, db: DbDep) -> Response:
    repo = UserRepository(db)
    user = repo.get(user_id)
    if user is None:
        raise NotFoundError("User not found")
    if user.id == admin.id:
        raise ConflictError("Use the account endpoint to delete yourself")
    repo.delete(user)
    return Response(status_code=204)


@router.get("/attempts", response_model=list[AttemptOut])
def list_attempts(
    _: AdminUser,
    container: ContainerDep,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[AttemptOut]:
    attempts = container.audit.list_attempts(offset=offset, limit=limit)
    return [AttemptOut.model_validate(a) for a in attempts]


@router.get("/stats", response_model=StatsOut)
def stats(_: AdminUser, container: ContainerDep, db: DbDep) -> StatsOut:
    buckets = [
        StatsBucket(mode=m, success=s, failure_reason=r, count=c)
        for m, s, r, c in container.audit.stats()
    ]
    return StatsOut(users=UserRepository(db).count(), attempts=buckets)
