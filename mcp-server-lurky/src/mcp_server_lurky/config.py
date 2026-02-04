"""
Configuration module for the MCP Lurky server.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# Load environment variables from the repo-root .env file (if present).
_project_root = Path(__file__).resolve().parents[2]
_env_file = _project_root / ".env"
load_dotenv(dotenv_path=_env_file)


class LurkyConfig(BaseSettings):
    """Lurky API configuration."""

    model_config = SettingsConfigDict(
        env_file=_env_file,
        env_file_encoding="utf-8",
        env_prefix="LURKY_",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
    )

    api_key: str | None = None
    base_url: str = "https://api.lurky.app"


class DatabaseConfig(BaseSettings):
    """Database configuration for Postgres cache."""

    model_config = SettingsConfigDict(
        env_file=_env_file,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    DB_NAME: str = "lurky_db"
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "postgres"
    DB_HOST: str = "localhost"
    DB_PORT_RAW: str = "5432"
    
    # Cache TTL defaults (in seconds)
    cache_ttl_search: int = 3600  # 1 hour
    cache_ttl_details: int = 86400  # 24 hours
    
    @computed_field
    @property
    def DB_PORT(self) -> str:
        return self.DB_PORT_RAW.split(":")[0] if ":" in self.DB_PORT_RAW else self.DB_PORT_RAW

    @computed_field
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+psycopg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"


class AppSettings(BaseSettings):
    """Application settings for the MCP Lurky server."""

    host: str = "0.0.0.0"
    port: int = 8000
    logging_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    hot_reload: bool = False

    lurky: LurkyConfig = LurkyConfig()
    database: DatabaseConfig = DatabaseConfig()

    model_config = SettingsConfigDict(
        env_file=_env_file,
        env_file_encoding="utf-8",
        env_prefix="MCP_LURKY_",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_app_settings() -> AppSettings:
    return AppSettings()
