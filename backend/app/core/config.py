"""Application configuration loaded from environment variables (prefix ``FA_``).

Nested groups use ``__`` as a delimiter, e.g. ``FA_MATCHING__THRESHOLD=0.4``.
"""

from __future__ import annotations

import base64
import hashlib
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
_DEV_JWT_SECRET = "dev-insecure-jwt-secret-change-me"


class AntiSpoofModelSettings(BaseModel):
    file: str
    crop_scale: float = Field(gt=1.0)
    weight: float = Field(default=1.0, gt=0.0)


class ModelSettings(BaseModel):
    directory: Path = BACKEND_DIR / "models"
    detector: str = "face_detection_yunet_2023mar.onnx"
    recognizer: str = "face_recognition_sface_2021dec.onnx"
    recognizer_version: str = "sface-2021dec"
    anti_spoof: list[AntiSpoofModelSettings] = Field(
        default_factory=lambda: [
            AntiSpoofModelSettings(file="MiniFASNetV2.onnx", crop_scale=2.7),
            AntiSpoofModelSettings(file="MiniFASNetV1SE.onnx", crop_scale=4.0),
        ]
    )
    onnx_providers: list[str] = Field(default_factory=lambda: ["CPUExecutionProvider"])


class DetectionSettings(BaseModel):
    score_threshold: float = Field(default=0.85, ge=0.0, le=1.0)
    nms_threshold: float = Field(default=0.3, ge=0.0, le=1.0)
    max_image_side: int = Field(default=1280, ge=160)


class QualitySettings(BaseModel):
    min_face_size: int = Field(default=90, ge=0, description="Minimal face bbox side in pixels")
    min_sharpness: float = Field(default=25.0, ge=0.0, description="Laplacian variance")
    min_brightness: float = Field(default=50.0, ge=0.0, le=255.0)
    max_brightness: float = Field(default=215.0, ge=0.0, le=255.0)
    secondary_face_area_ratio: float = Field(
        default=0.15,
        ge=0.0,
        le=1.0,
        description="A second face larger than this fraction of the main face is rejected",
    )


class PassiveLivenessSettings(BaseModel):
    threshold: float = Field(default=0.70, ge=0.0, le=1.0)
    min_frame_score: float = Field(
        default=0.30, ge=0.0, le=1.0, description="Any single frame below this fails the session"
    )


ActionName = Literal["turn_left", "turn_right", "look_up", "look_down"]


def _all_actions() -> list[ActionName]:
    return ["turn_left", "turn_right", "look_up", "look_down"]


class ActiveLivenessSettings(BaseModel):
    actions: list[ActionName] = Field(default_factory=_all_actions, min_length=1)
    steps: int = Field(default=2, ge=1, le=4, description="Number of random actions per challenge")
    center_max_yaw: float = Field(default=0.22, ge=0.0)
    yaw_threshold: float = Field(default=0.20, gt=0.0)
    pitch_threshold: float = Field(default=0.07, gt=0.0)
    min_frames_over_threshold: int = Field(default=2, ge=1)
    min_face_ratio: float = Field(
        default=0.8, ge=0.0, le=1.0, description="Share of frames that must contain a valid face"
    )

    @model_validator(mode="after")
    def _enough_actions(self) -> ActiveLivenessSettings:
        if self.steps > len(set(self.actions)):
            raise ValueError("active_liveness.steps exceeds the number of distinct actions")
        return self


class ChallengeSettings(BaseModel):
    ttl_seconds: int = Field(default=90, ge=10)
    frames_per_step: int = Field(default=5, ge=1, le=10)
    step_duration_ms: int = Field(default=2200, ge=500)
    lead_in_ms: int = Field(default=700, ge=0)


class MatchingSettings(BaseModel):
    threshold: float = Field(
        default=0.40, ge=-1.0, le=1.0, description="Cosine similarity (SFace reference: 0.363)"
    )
    consistency_threshold: float = Field(
        default=0.30, ge=-1.0, le=1.0, description="Min similarity of every frame to the session"
    )
    reject_duplicate_enrollment: bool = True


class SecuritySettings(BaseModel):
    jwt_secret: SecretStr = SecretStr(_DEV_JWT_SECRET)
    jwt_algorithm: str = "HS256"
    jwt_ttl_minutes: int = Field(default=30, ge=1)
    template_encryption_key: SecretStr | None = None
    expose_scores: bool = True
    lockout_max_failures: int = Field(default=5, ge=1)
    lockout_window_minutes: int = Field(default=15, ge=1)
    rate_limit_per_minute: int = Field(default=20, ge=1)
    max_request_bytes: int = Field(default=20 * 1024 * 1024, ge=1024)
    max_frame_bytes: int = Field(default=2 * 1024 * 1024, ge=1024)
    max_frames: int = Field(default=40, ge=1)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="FA_",
        env_nested_delimiter="__",
        env_file=".env",
        extra="ignore",
    )

    environment: Literal["development", "production", "test"] = "development"
    app_name: str = "Face Auth Anti-Spoofing"
    api_prefix: str = "/api/v1"
    log_level: str = "INFO"
    log_json: bool = False
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    database_url: str = f"sqlite:///{(BACKEND_DIR / 'data' / 'app.db').as_posix()}"
    run_migrations_on_startup: bool = True
    redis_url: str | None = None

    models: ModelSettings = Field(default_factory=ModelSettings)
    detection: DetectionSettings = Field(default_factory=DetectionSettings)
    quality: QualitySettings = Field(default_factory=QualitySettings)
    passive_liveness: PassiveLivenessSettings = Field(default_factory=PassiveLivenessSettings)
    active_liveness: ActiveLivenessSettings = Field(default_factory=ActiveLivenessSettings)
    challenge: ChallengeSettings = Field(default_factory=ChallengeSettings)
    matching: MatchingSettings = Field(default_factory=MatchingSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)

    @field_validator("database_url")
    @classmethod
    def _use_psycopg_driver(cls, value: str) -> str:
        """Hosting providers hand out ``postgres://`` URLs; SQLAlchemy needs an explicit driver."""
        for prefix in ("postgres://", "postgresql://"):
            if value.startswith(prefix):
                return "postgresql+psycopg://" + value[len(prefix) :]
        return value

    @model_validator(mode="after")
    def _validate_production(self) -> Settings:
        if self.environment != "production":
            return self
        problems = []
        if self.security.jwt_secret.get_secret_value() == _DEV_JWT_SECRET:
            problems.append("FA_SECURITY__JWT_SECRET must be set")
        if self.security.template_encryption_key is None:
            problems.append("FA_SECURITY__TEMPLATE_ENCRYPTION_KEY must be set")
        if self.security.expose_scores:
            problems.append("FA_SECURITY__EXPOSE_SCORES must be false")
        if problems:
            raise ValueError("Insecure production configuration: " + "; ".join(problems))
        return self

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    def template_key(self) -> bytes:
        """Fernet key for biometric templates.

        A valid Fernet key is used as is; any other secret (e.g. a value generated
        by the hosting platform) is stretched with SHA-256. Outside production a
        stable key is derived from the JWT secret so that a development database
        survives restarts without extra configuration.
        """
        configured = self.security.template_encryption_key
        secret = (configured or self.security.jwt_secret).get_secret_value()
        if configured is not None and _is_fernet_key(secret):
            return secret.encode()
        return base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest())


def _is_fernet_key(value: str) -> bool:
    try:
        return len(base64.urlsafe_b64decode(value.encode())) == 32
    except ValueError:
        return False


@lru_cache
def get_settings() -> Settings:
    return Settings()
