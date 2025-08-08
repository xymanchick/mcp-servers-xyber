from __future__ import annotations

from datetime import datetime, timezone
from pydantic import BaseModel, Field


class ParsedMessage(BaseModel):
    id: int = Field(..., description="Telegram message ID")
    date: datetime = Field(..., description="Message timestamp")
    text: str = Field(..., description="Message text content")
    views: int | None = Field(None, description="View count if available")
    forwards: int | None = Field(None, description="Forward count if available")


class ParsedChannel(BaseModel):
    channel_name: str = Field(..., description="Channel username without @")
    messages_count: int = Field(..., description="Number of messages returned")
    messages: list[ParsedMessage] = Field(default_factory=list)
    error: str | None = Field(None, description="Error if channel unavailable")


class TelegramParseResult(BaseModel):
    fetch_timestamp: datetime = Field(..., description="Fetch time")
    channels: dict[str, ParsedChannel] = Field(
        default_factory=dict, description="Per-channel parsed results"
    )

    @classmethod
    def create_now(cls, channels: dict[str, ParsedChannel]) -> "TelegramParseResult":
        return cls(fetch_timestamp=datetime.now(timezone.utc), channels=channels)


