from pydantic_settings import BaseSettings
from pydantic import Field


class ParserConfig(BaseSettings):
    api_id: int = Field(..., description="Telegram API ID")
    api_hash: str = Field(..., description="Telegram API Hash")
    string_session: str | None = Field(default=None, description="Telethon StringSession")

    model_config = {
        "env_prefix": "TELEGRAM_",
        "env_file": ".env",
    }


