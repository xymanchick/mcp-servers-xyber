"""
FastAPI dependency functions that expose shared service clients to routers and tools.

Main responsibility: Provide dependency injection for Telegram service clients.
"""

from fastapi import Request

from mcp_server_telegram.telegram import (
    _TelegramService,
    get_telegram_service as _get_telegram_service,
)


def get_telegram_service(token: str, channel: str) -> _TelegramService:
    """
    Dependency to get the TelegramService instance.

    For this server we use the globally cached TelegramService provided by the
    telegram module so that both REST and MCP calls share the same client.

    Args:
        token: The Telegram bot API token
        channel: The Telegram channel ID

    Returns:
        Cached TelegramService instance
    """
    return _get_telegram_service(token=token, channel=channel)
