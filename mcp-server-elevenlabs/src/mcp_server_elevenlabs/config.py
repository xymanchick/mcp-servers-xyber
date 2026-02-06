from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from pydantic import Field, computed_field
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)

# Define the path to the root .env file to ensure consistent loading
# src/mcp_server_elevenlabs/config.py -> src/mcp_server_elevenlabs/ -> src/ -> root
_project_root = Path(__file__).resolve().parent.parent.parent
_env_file = _project_root / ".env"

logger = logging.getLogger(__name__)


def _is_writable_dir_path(path: Path) -> bool:
    """
    Return True if `path` can be created (or is) a writable directory.

    We check the nearest existing parent for write+execute permissions.
    """
    try:
        p = path
        while not p.exists() and p != p.parent:
            p = p.parent
        if not p.exists():
            return False
        return os.access(p, os.W_OK | os.X_OK)
    except Exception:  # noqa: BLE001
        return False


class ElevenLabsSettings(BaseSettings):
    ELEVENLABS_API_KEY: Optional[str] = Field(default=None, env="ELEVENLABS_API_KEY")
    ELEVENLABS_VOICE_ID: Optional[str] = Field(default=None, env="ELEVENLABS_VOICE_ID")
    ELEVENLABS_MODEL_ID: Optional[str] = Field(default=None, env="ELEVENLABS_MODEL_ID")
    model_config = SettingsConfigDict(
        env_file=_env_file, env_file_encoding="utf-8", extra="ignore"
    )


class MediaSettings(BaseSettings):
    """Defines all media paths based on a single root directory."""

    MEDIA_HOST_DIR: Path | None = Field(default=None, env="MEDIA_HOST_DIR")
    MEDIA_CONTAINER_DIR: Path = Field(
        default=Path("/app/media"), env="MEDIA_CONTAINER_DIR"
    )

    @computed_field
    @property
    def media_root_dir(self) -> Path:
        """Dynamically provides the correct media root path based on environment."""
        candidates: list[Path] = []
        if self.MEDIA_HOST_DIR:
            candidates.append(self.MEDIA_HOST_DIR)
        candidates.append(self.MEDIA_CONTAINER_DIR)
        # Final safety fallback for container environments / misconfiguration.
        candidates.append(Path("/app/media"))
        candidates.append(Path("/tmp"))

        for candidate in candidates:
            if _is_writable_dir_path(candidate):
                if self.MEDIA_HOST_DIR and candidate != self.MEDIA_HOST_DIR:
                    logger.warning(
                        "MEDIA_HOST_DIR=%s is not writable/available; falling back to %s",
                        self.MEDIA_HOST_DIR,
                        candidate,
                    )
                return candidate

        # If everything fails, return the configured container dir and let mkdir raise a clear error.
        return self.MEDIA_CONTAINER_DIR

    @computed_field
    @property
    def voice_output_dir(self) -> Path:
        return self.media_root_dir / "voice" / "generated_audio"

    model_config = SettingsConfigDict(
        env_file=_env_file, env_file_encoding="utf-8", extra="ignore"
    )


class Settings(BaseSettings):
    # Logging
    logging_level: str = Field(default="INFO", env="LOGGING_LEVEL")

    # Server settings
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    hot_reload: bool = Field(default=False, env="HOT_RELOAD")

    # Nested settings
    media: MediaSettings = MediaSettings()
    elevenlabs: ElevenLabsSettings = ElevenLabsSettings()

    model_config = SettingsConfigDict(
        env_file=_env_file, env_file_encoding="utf-8", extra="ignore"
    )


# Global settings instance
settings = Settings()


def get_app_settings() -> Settings:
    return settings
