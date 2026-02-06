from __future__ import annotations

import logging
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
        if self.MEDIA_HOST_DIR:
            return self.MEDIA_HOST_DIR
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
