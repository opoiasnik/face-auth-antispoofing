"""Composition root: wires infrastructure objects shared for the application lifetime."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.biometrics.engine import BiometricEngine
from app.biometrics.factory import build_engine
from app.biometrics.types import ChallengeAction
from app.core.config import Settings
from app.core.rate_limit import InMemoryRateLimiter, RateLimiter, RedisRateLimiter
from app.core.security import TemplateCipher, TokenService
from app.db.session import create_db_engine, create_session_factory
from app.repositories.audit import AuditRepository
from app.services.challenges import (
    ChallengeService,
    ChallengeStore,
    InMemoryChallengeStore,
    RedisChallengeStore,
)

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class Container:
    settings: Settings
    db_engine: Engine
    session_factory: sessionmaker[Session]
    challenges: ChallengeService
    rate_limiter: RateLimiter
    tokens: TokenService
    cipher: TemplateCipher
    audit: AuditRepository
    biometrics: BiometricEngine | None = None
    biometrics_error: str | None = None


def build_container(
    settings: Settings, *, biometrics: BiometricEngine | None = None, load_models: bool = True
) -> Container:
    db_engine = create_db_engine(settings.database_url)
    session_factory = create_session_factory(db_engine)

    store: ChallengeStore
    limiter: RateLimiter
    if settings.redis_url:
        from redis import Redis

        client = Redis.from_url(settings.redis_url)
        store, limiter = RedisChallengeStore(client), RedisRateLimiter(client)
    else:
        store, limiter = InMemoryChallengeStore(), InMemoryRateLimiter()

    container = Container(
        settings=settings,
        db_engine=db_engine,
        session_factory=session_factory,
        challenges=ChallengeService(
            store,
            settings.challenge,
            [ChallengeAction(a) for a in settings.active_liveness.actions],
            settings.active_liveness.steps,
        ),
        rate_limiter=limiter,
        tokens=TokenService(
            settings.security.jwt_secret.get_secret_value(),
            settings.security.jwt_algorithm,
            settings.security.jwt_ttl_minutes,
        ),
        cipher=TemplateCipher(settings.template_key()),
        audit=AuditRepository(session_factory),
        biometrics=biometrics,
    )
    if biometrics is None and load_models:
        try:
            container.biometrics = build_engine(settings)
            logger.info("Biometric models loaded from %s", settings.models.directory)
        except FileNotFoundError as exc:
            container.biometrics_error = f"Model file missing: {exc}"
            logger.error("%s - run `python scripts/download_models.py`", container.biometrics_error)
    return container
