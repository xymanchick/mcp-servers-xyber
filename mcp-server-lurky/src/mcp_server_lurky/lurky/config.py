import logging
from functools import lru_cache
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class LurkyServiceConfig(BaseSettings):
    """
    Configuration for the Lurky service.
    """

    model_config = SettingsConfigDict(
        env_prefix="LURKY_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    api_key: str = ""
    base_url: str = "https://api.lurky.app"
    timeout_seconds: int = 30

    @field_validator("api_key")
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        if not v or not v.strip():
            logger.warning(
                "LURKY_API_KEY is not set or is whitespace-only. Requests to the Lurky API will fail with 401 errors."
            )
        return v


@lru_cache(maxsize=1)
def get_lurky_config() -> LurkyServiceConfig:
    return LurkyServiceConfig()
