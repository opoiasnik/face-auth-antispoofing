"""ORM models."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    full_name: Mapped[str | None] = mapped_column(String(128))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    templates: Mapped[list[FaceTemplate]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )


class FaceTemplate(Base):
    """Encrypted face embedding. Raw images are never stored."""

    __tablename__ = "face_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    encrypted_embedding: Mapped[bytes] = mapped_column(LargeBinary)
    model_version: Mapped[str] = mapped_column(String(32))
    liveness_score: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped[User] = relationship(back_populates="templates")


class AuthAttempt(Base):
    """Audit log of every enrollment / authentication attempt."""

    __tablename__ = "auth_attempts"
    __table_args__ = (Index("ix_auth_attempts_username_created", "username", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    username: Mapped[str | None] = mapped_column(String(64))
    mode: Mapped[str] = mapped_column(String(16))
    success: Mapped[bool] = mapped_column(Boolean, index=True)
    failure_reason: Mapped[str | None] = mapped_column(String(48))
    match_score: Mapped[float | None] = mapped_column(Float)
    passive_score: Mapped[float | None] = mapped_column(Float)
    active_passed: Mapped[bool | None] = mapped_column(Boolean)
    frames: Mapped[int] = mapped_column(Integer, default=0)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    client_ip: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(256))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )
