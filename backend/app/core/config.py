"""Application settings loaded from environment variables (12-Factor App)."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/.env, resolved from this file so it works no matter where you run the
# command from (uvicorn, alembic, pytest).
ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: Literal["development", "production"] = "development"

    # Contains the DB password, so it is a secret too.
    database_url: SecretStr

    jwt_secret_key: SecretStr
    # Only allow the algorithm we actually use (prevents "algorithm confusion").
    jwt_algorithm: Literal["HS256"] = "HS256"
    access_token_expire_minutes: int = Field(default=30, gt=0)

    cors_origins: list[str] = ["http://localhost:5173"]

    cookie_name: str = "tat_access_token"
    cookie_secure: bool = False

    @field_validator("jwt_secret_key")
    @classmethod
    def _jwt_secret_min_length(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value()) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters long")
        return value


@lru_cache
def get_settings() -> Settings:
    """Read the environment once and reuse the same Settings instance."""
    return Settings()
