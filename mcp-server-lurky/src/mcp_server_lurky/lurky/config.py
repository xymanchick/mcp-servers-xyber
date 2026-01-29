from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


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


@lru_cache(maxsize=1)
def get_lurky_config() -> LurkyServiceConfig:
    return LurkyServiceConfig()
