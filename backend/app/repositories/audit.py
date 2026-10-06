from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import AuthAttempt


class AuditRepository:
    """Audit records are written in their own transaction so they survive request rollbacks."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def record(self, attempt: AuthAttempt) -> None:
        with self._session_factory() as session, session.begin():
            session.add(attempt)

    def recent_failures(self, username: str, since: datetime) -> int:
        stmt = select(func.count(AuthAttempt.id)).where(
            AuthAttempt.username == username,
            AuthAttempt.success.is_(False),
            AuthAttempt.mode == "verify",
            AuthAttempt.created_at >= since,
        )
        with self._session_factory() as session:
            return int(session.scalar(stmt) or 0)

    def list_attempts(
        self, *, user_id: int | None = None, offset: int = 0, limit: int = 50
    ) -> Sequence[AuthAttempt]:
        stmt = select(AuthAttempt).order_by(AuthAttempt.created_at.desc(), AuthAttempt.id.desc())
        if user_id is not None:
            stmt = stmt.where(AuthAttempt.user_id == user_id)
        with self._session_factory() as session:
            return session.scalars(stmt.offset(offset).limit(limit)).all()

    def stats(self) -> list[tuple[str, bool, str | None, int]]:
        """Counts grouped by (mode, success, failure_reason)."""
        stmt = select(
            AuthAttempt.mode,
            AuthAttempt.success,
            AuthAttempt.failure_reason,
            func.count(AuthAttempt.id),
        ).group_by(AuthAttempt.mode, AuthAttempt.success, AuthAttempt.failure_reason)
        with self._session_factory() as session:
            return [(m, s, r, int(c)) for m, s, r, c in session.execute(stmt).all()]
