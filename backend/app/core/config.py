from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
import json


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Database ──────────────────────────────────────────────────────────────
    DATABASE_URL: str

    # ── Redis ─────────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── Keycloak ──────────────────────────────────────────────────────────────
    KEYCLOAK_URL: str
    KEYCLOAK_REALM: str = "exocortex"
    KEYCLOAK_CLIENT_ID: str = "exocortex-api"

    # ── CORS ──────────────────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return json.loads(v)
        return v

    # ── OpenTelemetry ─────────────────────────────────────────────────────────
    OTEL_SERVICE_NAME: str = "exocortex-api"
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://localhost:4317"

    # ── Application secrets ───────────────────────────────────────────────────
    # Fernet key for encrypting SystemConfig secrets stored in DB.
    # Generate: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    EXOCORTEX_SECRET_KEY: str

    @field_validator("EXOCORTEX_SECRET_KEY")
    @classmethod
    def validate_fernet_key(cls, v: str) -> str:
        try:
            from cryptography.fernet import Fernet
            Fernet(v.encode())
        except Exception as exc:
            raise ValueError(
                "EXOCORTEX_SECRET_KEY must be a valid Fernet key. "
                "Generate with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            ) from exc
        return v

    # ── Sentry ────────────────────────────────────────────────────────────────
    SENTRY_DSN: str | None = None

    # ── Application ───────────────────────────────────────────────────────────
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    # Public URL of this API (used for OAuth callbacks, webhooks)
    BASE_URL: str = "http://localhost:8000"

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"


settings = Settings()
