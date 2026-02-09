import logging
from functools import lru_cache
from typing import Iterable

from mcp_server_telegram_parser.schemas import (ParsedChannel, ParsedMessage,
                                                TelegramParseResult)
from mcp_server_telegram_parser.telegram.config import (ParserAuthError,
                                                        ParserConfig)
from telethon import TelegramClient
from telethon.sessions import StringSession

logger = logging.getLogger(__name__)


class TelegramParserService:
    def __init__(self, config: ParserConfig) -> None:
        self.config = config

    async def parse_channels(
        self, channels: Iterable[str], limit: int
    ) -> TelegramParseResult:
        results: dict[str, ParsedChannel] = {}
        try:
            client = TelegramClient(
                StringSession(self.config.string_session),
                self.config.api_id,
                self.config.api_hash,
            )

        except Exception as e:
            raise ParserAuthError(
                "Authentication failed. The common case is due to invalid TELEGRAM_STRING_SESSION. Generate a new string and update TELEGRAM_STRING_SESSION."
            ) from e

        async with client as client:
            for name in channels:
                key = name.strip().lstrip("@")
                try:
                    entity = await client.get_entity(key)
                    messages = await client.get_messages(entity, limit=limit)
                    parsed: list[ParsedMessage] = []
                    for m in messages:
                        if not m or not getattr(m, "text", None):
                            continue
                        parsed.append(
                            ParsedMessage(
                                id=int(m.id),
                                date=m.date,
                                text=m.text,
                                views=getattr(m, "views", None),
                                forwards=getattr(m, "forwards", None),
                            )
                        )
                    results[key] = ParsedChannel(
                        channel_name=key,
                        messages_count=len(parsed),
                        messages=parsed,
                    )
                except Exception:
                    results[key] = ParsedChannel(
                        channel_name=key,
                        messages_count=0,
                        messages=[],
                        error=f"channel {key} is not available now",
                    )
        return TelegramParseResult.create_now(channels=results)


@lru_cache(maxsize=1)
def get_parser_service() -> TelegramParserService:
    return TelegramParserService(ParserConfig())
