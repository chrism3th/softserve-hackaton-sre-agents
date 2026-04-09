"""Application settings loaded from environment."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration.

    Values are loaded from environment variables. A ``.env`` file is used
    as a fallback for local development only.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "hackaton-backend"
    env: Literal["dev", "test", "prod"] = "dev"
    log_level: str = "INFO"

    # API
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@db:5432/app"

    # Cache
    redis_url: str = "redis://redis:6379/0"

    # LLM
    anthropic_api_key: str = ""
    llm_model: str = "claude-sonnet-4-6"
    llm_max_tokens: int = 1024
    llm_timeout_seconds: float = 60.0

    # Linear
    linear_api_key: str = ""
    linear_team_key: str = "TEA"
    linear_api_url: str = "https://api.linear.app/graphql"
    linear_webhook_secret: str = ""

    # GitHub
    github_webhook_secret: str = ""

    # Phoenix tracing
    phoenix_collector_endpoint: str = "http://phoenix:6006"
    phoenix_project_name: str = "sre-agents"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
