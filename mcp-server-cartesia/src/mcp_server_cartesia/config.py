"""
Application configuration for the Cartesia MCP Server.

Main responsibility: Define and load application settings.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class AppSettings(BaseSettings):
    """
    Application settings for the MCP Cartesia Server.

    Configuration can be provided via environment variables using the prefix:
    MCP_CARTESIA_HOST=0.0.0.0
    MCP_CARTESIA_PORT=8005
    MCP_CARTESIA_LOGGING_LEVEL=INFO
    MCP_CARTESIA_HOT_RELOAD=false
    """

    # --- Server Settings ---
    host: str = "0.0.0.0"
    port: int = 8005
    logging_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    hot_reload: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="MCP_CARTESIA_",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_app_settings() -> AppSettings:
    return AppSettings()
