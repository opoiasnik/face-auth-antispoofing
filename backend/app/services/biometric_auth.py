"""Use cases: enrollment, re-enrollment, 1:1 verification and 1:N identification."""

from __future__ import annotations

import logging
import time
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import numpy as np
from sqlalchemy.orm import Session

from app.biometrics.embedder import TemplateMatcher
from app.biometrics.engine import BiometricEngine
from app.biometrics.image import decode_base64_image
from app.biometrics.types import RejectionReason, SessionResult
from app.core.config import Settings
from app.core.errors import (
    AppError,
    BiometricRejectedError,
    ChallengeError,
    ConflictError,
    TooManyRequestsError,
)
from app.core.security import TemplateCipher
from app.db.models import AuthAttempt, FaceTemplate, User
from app.repositories.audit import AuditRepository
from app.repositories.users import TemplateRepository, UserRepository
from app.services.challenges import ChallengePurpose, ChallengeService

logger = logging.getLogger(__name__)

_REJECTION_MESSAGES: dict[RejectionReason, str] = {
    RejectionReason.QUALITY: "Face could not be captured in sufficient quality",
    RejectionReason.PASSIVE_SPOOF: "Presentation attack suspected (spoof detected)",
    RejectionReason.ACTIVE_CHALLENGE_FAILED: "Liveness challenge was not completed",
    RejectionReason.IDENTITY_INCONSISTENT: "Face changed during the capture session",
    RejectionReason.NO_MATCH: "Biometric verification failed",
    RejectionReason.DUPLICATE_FACE: "This face is already enrolled",
}


@dataclass(frozen=True, slots=True)
class ClientContext:
    ip: str | None = None
    user_agent: str | None = None


@dataclass(frozen=True, slots=True)
class CaptureSubmission:
    challenge_id: str
    frames: Sequence[tuple[int, str]]  # (step index, base64 image)


@dataclass(slots=True)
class AuthOutcome:
    user: User
    session: SessionResult
    match_score: float | None = None


@dataclass(slots=True)
class _AttemptDraft:
    mode: str
    username: str | None
    user_id: int | None = None
    match_score: float | None = None
    session: SessionResult | None = None
    frames: int = 0
    extra: dict[str, object] = field(default_factory=dict)


class BiometricAuthService:
    def __init__(
        self,
        *,
        db: Session,
        engine: BiometricEngine,
        challenges: ChallengeService,
        cipher: TemplateCipher,
        audit: AuditRepository,
        settings: Settings,
    ) -> None:
        self._db = db
        self._engine = engine
        self._challenges = challenges
        self._cipher = cipher
        self._audit = audit
        self._settings = settings
        self._users = UserRepository(db)
        self._templates = TemplateRepository(db)
        self._matcher = TemplateMatcher(settings.matching.threshold)

    # -- use cases ----------------------------------------------------------------------------

    def enroll(
        self,
        username: str,
        full_name: str | None,
        submission: CaptureSubmission,
        ctx: ClientContext,
    ) -> AuthOutcome:
        with self._attempt("enroll", ctx, username) as draft:
            if self._users.get_by_username(username) is not None:
                raise ConflictError("Username is already taken")
            session = self._run_session(ChallengePurpose.ENROLL, submission, draft)
            assert session.template is not None
            self._ensure_not_enrolled(session.template)

            user = self._users.add(User(username=username, full_name=full_name))
            self._templates.add(self._new_template(user.id, session))
            draft.user_id = user.id
            return AuthOutcome(user=user, session=session)

    def reenroll(
        self, user: User, submission: CaptureSubmission, ctx: ClientContext
    ) -> AuthOutcome:
        with self._attempt("reenroll", ctx, user.username) as draft:
            draft.user_id = user.id
            session = self._run_session(ChallengePurpose.ENROLL, submission, draft)
            assert session.template is not None
            # the new template must still belong to the same person
            outcome = self._match_user(user, session.template, draft)
            self._templates.replace_for_user(user.id, self._new_template(user.id, session))
            return AuthOutcome(user=user, session=session, match_score=outcome)

    def verify(
        self, username: str, submission: CaptureSubmission, ctx: ClientContext
    ) -> AuthOutcome:
        with self._attempt("verify", ctx, username) as draft:
            self._check_lockout(username)
            session = self._run_session(ChallengePurpose.AUTHENTICATE, submission, draft)
            assert session.template is not None
            user = self._users.get_by_username(username)
            if user is None or not user.is_active:
                raise self._rejection(RejectionReason.NO_MATCH, session)
            draft.user_id = user.id  # failed attempts are visible in the user's own history
            score = self._match_user(user, session.template, draft)
            return AuthOutcome(user=user, session=session, match_score=score)

    def identify(self, submission: CaptureSubmission, ctx: ClientContext) -> AuthOutcome:
        with self._attempt("identify", ctx, None) as draft:
            session = self._run_session(ChallengePurpose.AUTHENTICATE, submission, draft)
            assert session.template is not None
            result = self._matcher.identify(session.template, self._gallery())
            draft.match_score = result.score
            if not result.matched or result.key is None:
                raise self._rejection(RejectionReason.NO_MATCH, session, score=result.score)
            user = result.key
            draft.user_id, draft.username = user.id, user.username
            return AuthOutcome(user=user, session=session, match_score=result.score)

    # -- helpers ------------------------------------------------------------------------------

    def _run_session(
        self, purpose: ChallengePurpose, submission: CaptureSubmission, draft: _AttemptDraft
    ) -> SessionResult:
        challenge = self._challenges.consume(submission.challenge_id, purpose)
        limits = self._settings.security
        draft.frames = len(submission.frames)
        if not submission.frames or len(submission.frames) > limits.max_frames:
            raise ChallengeError("Invalid number of frames")
        steps_present = {step for step, _ in submission.frames}
        if steps_present != set(range(len(challenge.actions))):
            raise ChallengeError("Frames must cover every challenge step")

        frames = [
            (
                step,
                decode_base64_image(
                    data,
                    max_bytes=limits.max_frame_bytes,
                    max_side=self._settings.detection.max_image_side,
                ),
            )
            for step, data in sorted(submission.frames, key=lambda f: f[0])
        ]
        session = self._engine.evaluate_session(challenge.actions, frames)
        draft.session = session
        if not session.passed:
            assert session.rejection is not None
            raise self._rejection(session.rejection, session)
        return session

    def _match_user(self, user: User, probe: np.ndarray, draft: _AttemptDraft) -> float:
        references = [
            self._cipher.decrypt(t.encrypted_embedding)
            for t in self._templates.for_user(user.id, self._engine.recognizer_version)
        ]
        result = self._matcher.verify(probe, references)
        draft.match_score = result.score
        if not result.matched:
            assert draft.session is not None
            raise self._rejection(RejectionReason.NO_MATCH, draft.session, score=result.score)
        return result.score

    def _gallery(self) -> Iterator[tuple[User, np.ndarray]]:
        for template in self._templates.gallery(self._engine.recognizer_version):
            yield template.user, self._cipher.decrypt(template.encrypted_embedding)

    def _ensure_not_enrolled(self, template: np.ndarray) -> None:
        if not self._settings.matching.reject_duplicate_enrollment:
            return
        result = self._matcher.identify(template, self._gallery())
        if result.matched:
            raise ConflictError(
                _REJECTION_MESSAGES[RejectionReason.DUPLICATE_FACE],
                details={"reason": RejectionReason.DUPLICATE_FACE.value},
            )

    def _new_template(self, user_id: int, session: SessionResult) -> FaceTemplate:
        assert session.template is not None
        return FaceTemplate(
            user_id=user_id,
            encrypted_embedding=self._cipher.encrypt(session.template),
            model_version=self._engine.recognizer_version,
            liveness_score=session.passive_score,
        )

    def _check_lockout(self, username: str) -> None:
        sec = self._settings.security
        since = datetime.now(UTC) - timedelta(minutes=sec.lockout_window_minutes)
        if self._audit.recent_failures(username, since) >= sec.lockout_max_failures:
            raise TooManyRequestsError(
                "Too many failed attempts, account temporarily locked",
                details={"retry_after_minutes": sec.lockout_window_minutes},
            )

    def _rejection(
        self, reason: RejectionReason, session: SessionResult, *, score: float | None = None
    ) -> BiometricRejectedError:
        details: dict[str, object] = {}
        if self._settings.security.expose_scores:
            details = session.summary()
            if score is not None:
                details["match_score"] = round(score, 4)
        elif session.quality_issues:
            # quality hints are safe to expose and help the user to retry
            details = {"quality_issues": session.quality_issues}
        return BiometricRejectedError(reason.value, _REJECTION_MESSAGES[reason], details=details)

    @contextmanager
    def _attempt(
        self, mode: str, ctx: ClientContext, username: str | None
    ) -> Iterator[_AttemptDraft]:
        """Unit of work + audit trail: commit/rollback the request, then log the attempt."""
        draft = _AttemptDraft(mode=mode, username=username)
        started = time.perf_counter()
        failure: str | None = None
        try:
            yield draft
            self._db.commit()
        except BiometricRejectedError as exc:
            failure = exc.reason
            raise
        except AppError as exc:
            failure = str(exc.details.get("reason", exc.code))
            raise
        except Exception:
            failure = "internal_error"
            raise
        finally:
            if failure is not None:
                self._db.rollback()
            self._record(draft, ctx, failure, started)

    def _record(
        self, draft: _AttemptDraft, ctx: ClientContext, failure: str | None, started: float
    ) -> None:
        session = draft.session
        attempt = AuthAttempt(
            user_id=draft.user_id if failure is None or draft.mode != "enroll" else None,
            username=draft.username,
            mode=draft.mode,
            success=failure is None,
            failure_reason=failure,
            match_score=draft.match_score,
            passive_score=session.passive_score if session else None,
            active_passed=session.active.passed if session and session.active else None,
            frames=draft.frames,
            duration_ms=int((time.perf_counter() - started) * 1000),
            client_ip=ctx.ip,
            user_agent=(ctx.user_agent or "")[:256] or None,
        )
        try:
            self._audit.record(attempt)
        except Exception:  # auditing must never break authentication
            logger.exception("Failed to write audit record")
        logger.info(
            "biometric %s user=%s success=%s reason=%s",
            draft.mode,
            draft.username,
            failure is None,
            failure,
        )
