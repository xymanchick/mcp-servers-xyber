"""
Configuration module for the MCP YouTube server.
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# Load environment variables from the repo-root .env file (if present)
# File location: <repo>/src/mcp_server_youtube/config.py -> repo root is 3 levels up
_project_root = Path(__file__).resolve().parents[2]
_env_file = _project_root / ".env"
load_dotenv(dotenv_path=_env_file)


class DatabaseConfig(BaseModel):
    """Database configuration."""

    DB_NAME: str = os.getenv("DB_NAME", "mcp_youtube")
    DB_USER: str = os.getenv("DB_USER", "postgres")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "postgres")
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT_RAW: str = os.getenv("DB_PORT", "5432")
    DB_PORT: str = ""
    DATABASE_URL: str = ""

    @model_validator(mode="after")
    def compute_database_url(self):
        """Compute DATABASE_URL and DB_PORT after fields are set."""
        self.DB_PORT = (
            self.DB_PORT_RAW.split(":")[0]
            if ":" in self.DB_PORT_RAW
            else self.DB_PORT_RAW
        )
        # Use postgresql+psycopg:// to use psycopg3 driver (not psycopg2)
        self.DATABASE_URL = f"postgresql+psycopg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        # Avoid leaking credentials in logs
        logger.info(
            "Database configured: postgresql+psycopg://%s:***@%s:%s/%s",
            self.DB_USER,
            self.DB_HOST,
            self.DB_PORT,
            self.DB_NAME,
        )
        return self


class ApifyConfig(BaseModel):
    """Apify API configuration."""

    # Loaded from process env (dotenv above ensures `.env` is applied).
    # Prefer the common `APIFY_TOKEN`, but allow nested form too.
    apify_token: str | None = os.getenv("APIFY_TOKEN") or os.getenv(
        "MCP_YOUTUBE__APIFY__APIFY_TOKEN"
    )


class YouTubeConfig(BaseModel):
    """YouTube service configuration."""

    delay_between_requests: float = Field(default=1.0, env="DELAY_BETWEEN_REQUESTS")
    max_results: int = Field(default=10, env="MAX_RESULTS")
    num_videos: int = Field(default=5, env="NUM_VIDEOS")
    query: str = Field(default="quantum computing basics", env="QUERY")


class LoggingConfig(BaseModel):
    """Logging configuration."""

    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(
        default="%(asctime)s [%(levelname)s] %(name)s: %(message)s", env="LOG_FORMAT"
    )
    log_file: str = Field(default="logs/mcp_youtube.log", env="LOG_FILE")


class AppSettings(BaseSettings):
    """
    Application settings for the MCP YouTube Server.
    """

    # --- Server Settings ---
    host: str = "0.0.0.0"
    port: int = 8002
    logging_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    hot_reload: bool = False

    # --- Nested Configurations ---
    youtube: YouTubeConfig = YouTubeConfig()
    apify: ApifyConfig = ApifyConfig()
    logging: LoggingConfig = LoggingConfig()
    database: DatabaseConfig = DatabaseConfig()

    model_config = SettingsConfigDict(
        env_file=_env_file,
        env_file_encoding="utf-8",
        env_prefix="MCP_YOUTUBE_",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_app_settings() -> AppSettings:
    return AppSettings()
