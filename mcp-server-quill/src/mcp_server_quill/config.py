"""
Configuration module for the MCP Quill server.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# Load environment variables from the repo-root .env file (if present).
_src_dir = Path(__file__).resolve().parent
_project_root = _src_dir.parent.parent
_env_file = _project_root / ".env"
load_dotenv(dotenv_path=_env_file)


class QuillConfig(BaseSettings):
    """Quill API configuration."""

    model_config = SettingsConfigDict(
        env_file=_env_file,
        env_file_encoding="utf-8",
        env_prefix="QUILL_",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
    )

    api_key: str | None = None
    base_url: str = "https://check-api.quillai.network/api/v1"


class DexScreenerConfig(BaseSettings):
    """DexScreener API configuration."""

    model_config = SettingsConfigDict(
        env_file=_env_file,
        env_file_encoding="utf-8",
        env_prefix="DEXSCREENER_",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
    )

    base_url: str = "https://api.dexscreener.com/latest/dex/search"


class AppSettings(BaseSettings):
    """Application settings for the MCP Quill server."""

    host: str = "0.0.0.0"
    port: int = 8000
    logging_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    hot_reload: bool = False

    quill: QuillConfig = QuillConfig()
    dexscreener: DexScreenerConfig = DexScreenerConfig()

    model_config = SettingsConfigDict(
        env_file=_env_file,
        env_file_encoding="utf-8",
        env_prefix="MCP_QUILL_",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_app_settings() -> AppSettings:
    return AppSettings()
