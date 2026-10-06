from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.db.models import FaceTemplate, User


class UserRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, user_id: int) -> User | None:
        return self._session.get(User, user_id)

    def get_by_username(self, username: str) -> User | None:
        return self._session.scalar(select(User).where(User.username == username))

    def list_page(self, *, offset: int = 0, limit: int = 100) -> Sequence[User]:
        stmt = select(User).order_by(User.id).offset(offset).limit(limit)
        return self._session.scalars(stmt).all()

    def count(self) -> int:
        return int(self._session.scalar(select(func.count(User.id))) or 0)

    def add(self, user: User) -> User:
        self._session.add(user)
        self._session.flush()
        return user

    def delete(self, user: User) -> None:
        self._session.delete(user)
        self._session.flush()


class TemplateRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def for_user(self, user_id: int, model_version: str) -> Sequence[FaceTemplate]:
        stmt = select(FaceTemplate).where(
            FaceTemplate.user_id == user_id, FaceTemplate.model_version == model_version
        )
        return self._session.scalars(stmt).all()

    def gallery(self, model_version: str) -> Sequence[FaceTemplate]:
        """All templates of active users (for 1:N identification)."""
        stmt = (
            select(FaceTemplate)
            .join(User)
            .where(User.is_active.is_(True), FaceTemplate.model_version == model_version)
            .options(selectinload(FaceTemplate.user))
        )
        return self._session.scalars(stmt).all()

    def add(self, template: FaceTemplate) -> FaceTemplate:
        self._session.add(template)
        self._session.flush()
        return template

    def replace_for_user(self, user_id: int, template: FaceTemplate) -> FaceTemplate:
        for existing in self._session.scalars(
            select(FaceTemplate).where(FaceTemplate.user_id == user_id)
        ):
            self._session.delete(existing)
        return self.add(template)
