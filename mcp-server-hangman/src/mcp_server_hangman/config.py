import os
from functools import lru_cache

from pydantic_settings import BaseSettings


class AppSettings(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 8015
    hot_reload: bool = False

    class Config:
        env_prefix = "MCP_HANGMAN_"
        case_sensitive = False


@lru_cache
def get_app_settings() -> AppSettings:
    return AppSettings(
        host=os.getenv("MCP_HANGMAN_HOST", "0.0.0.0"),
        port=int(os.getenv("MCP_HANGMAN_PORT", "8015")),
        hot_reload=os.getenv("MCP_HANGMAN_RELOAD", "false").lower()
        in ("true", "1", "t", "yes"),
    )
