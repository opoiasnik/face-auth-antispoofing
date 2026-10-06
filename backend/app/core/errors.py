"""Domain exceptions and their mapping to HTTP responses."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class AppError(Exception):
    status_code = 400
    code = "bad_request"

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class ConflictError(AppError):
    status_code = 409
    code = "conflict"


class UnauthorizedError(AppError):
    status_code = 401
    code = "unauthorized"


class ForbiddenError(AppError):
    status_code = 403
    code = "forbidden"


class TooManyRequestsError(AppError):
    status_code = 429
    code = "too_many_requests"


class PayloadTooLargeError(AppError):
    status_code = 413
    code = "payload_too_large"


class InvalidImageError(AppError):
    status_code = 422
    code = "invalid_image"


class ChallengeError(AppError):
    status_code = 400
    code = "invalid_challenge"


class ServiceUnavailableError(AppError):
    status_code = 503
    code = "service_unavailable"


class BiometricRejectedError(AppError):
    """Raised when a biometric session fails (quality, liveness or matching)."""

    status_code = 401
    code = "biometric_rejected"

    def __init__(self, reason: str, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message, details=details)
        self.reason = reason


def _error_body(code: str, message: str, details: dict[str, Any] | None = None) -> dict:
    return {"error": {"code": code, "message": message, "details": details or {}}}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(BiometricRejectedError)
    async def _biometric(_: Request, exc: BiometricRejectedError) -> JSONResponse:
        details = {"reason": exc.reason, **exc.details}
        return JSONResponse(
            status_code=exc.status_code, content=_error_body(exc.code, exc.message, details)
        )

    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code, content=_error_body(exc.code, exc.message, exc.details)
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [{"loc": list(e.get("loc", ())), "msg": e.get("msg", "")} for e in exc.errors()]
        return JSONResponse(
            status_code=422,
            content=_error_body("validation_error", "Invalid request", {"errors": errors}),
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500, content=_error_body("internal_error", "Internal server error")
        )
