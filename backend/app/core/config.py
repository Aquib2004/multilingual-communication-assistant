"""Application settings, loaded entirely from the environment.

Never hard-code a credential. Every provider-specific value here is optional
and only required when the matching provider is selected.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ProviderName = Literal["mock", "openai", "local"]

#: Minimum number of target languages the project specification requires.
MIN_TARGET_LANGUAGES = 2

#: Hard cap on a single source message, in characters.
MAX_MESSAGE_CHARS = 5000


class Settings(BaseSettings):
    """Runtime configuration.

    Values are read from environment variables and from a local ``.env`` file
    that is git-ignored. See ``.env.example`` for the documented list.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Application --------------------------------------------------------
    app_env: str = "development"
    app_name: str = "multilingual-communication-assistant"
    version: str = "0.1.0"
    log_level: str = "INFO"
    api_v1_prefix: str = "/api"

    #: When false, message bodies are never written to logs. Keep false in prod.
    log_message_content: bool = False

    #: Comma-separated CORS allowlist.
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # --- Database -----------------------------------------------------------
    database_url: str = "sqlite+aiosqlite:///./app.db"
    database_echo: bool = False
    db_pool_size: int = Field(default=5, ge=1, le=50)
    db_max_overflow: int = Field(default=10, ge=0, le=100)

    # --- AI provider --------------------------------------------------------
    ai_provider: ProviderName = "mock"

    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"
    openai_timeout_seconds: float = Field(default=60.0, gt=0)
    openai_max_retries: int = Field(default=2, ge=0, le=10)

    local_base_url: str = "http://localhost:11434/v1"
    local_api_key: str = "not-needed"
    local_model: str = "llama3.1"
    local_timeout_seconds: float = Field(default=120.0, gt=0)

    # --- Privacy ------------------------------------------------------------
    data_retention_days: int = Field(default=30, ge=1, le=3650)

    # --- Limits -------------------------------------------------------------
    max_message_chars: int = Field(default=MAX_MESSAGE_CHARS, ge=100, le=100_000)
    min_target_languages: int = Field(default=MIN_TARGET_LANGUAGES, ge=1, le=10)
    max_target_languages: int = Field(default=3, ge=1, le=10)

    @field_validator("log_level")
    @classmethod
    def _validate_log_level(cls, value: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        level = value.upper()
        if level not in allowed:
            msg = f"LOG_LEVEL must be one of {sorted(allowed)}, got {value!r}"
            raise ValueError(msg)
        return level

    @field_validator("database_url")
    @classmethod
    def _validate_database_url(cls, value: str) -> str:
        if not value.strip():
            msg = "DATABASE_URL must not be empty"
            raise ValueError(msg)
        # Fail fast on an async driver mismatch rather than at first request.
        if "sqlite:///" in value and "aiosqlite" not in value:
            msg = "SQLite URLs must use the async driver: sqlite+aiosqlite:///path"
            raise ValueError(msg)
        if "postgresql://" in value and "psycopg" not in value:
            msg = "PostgreSQL URLs must use the driver: postgresql+psycopg://..."
            raise ValueError(msg)
        return value

    # --- Derived helpers ----------------------------------------------------

    @property
    def cors_origin_list(self) -> list[str]:
        """The CORS allowlist as a list of origins."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        """True when running with ``APP_ENV=production``."""
        return self.app_env.lower() in {"production", "prod"}

    @property
    def is_sqlite(self) -> bool:
        """True when the configured database is SQLite."""
        return self.database_url.startswith("sqlite")

    @property
    def should_log_message_content(self) -> bool:
        """Whether message bodies may be logged.

        Always false in production, regardless of configuration. This is a
        deliberate safety floor, not a default.
        """
        if self.is_production:
            return False
        return self.log_message_content


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached application settings.

    Cached so the environment is parsed once. Tests that need different values
    should call :func:`get_settings.cache_clear` after patching the environment.
    """
    return Settings()
