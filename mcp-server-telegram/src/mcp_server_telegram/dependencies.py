"""
FastAPI dependency functions that expose shared service clients to routers and tools.

Main responsibility: Provide dependency injection for Telegram service clients.
"""

import logging

from mcp_server_telegram.telegram import _TelegramService
from mcp_server_telegram.telegram import \
    get_telegram_service as create_telegram_service

logger = logging.getLogger(__name__)


class DependencyContainer:
    """
    Centralized container for all application dependencies.

    Note: The Telegram service uses per-request parameterized instances
    that are cached with lru_cache in the telegram module. This container
    provides a consistent interface for accessing the service factory.

    Usage:
        # In route handlers:
        telegram_service = get_telegram_service(token=token, channel=channel)
    """

    @classmethod
    def initialize(cls) -> None:
        """
        Initialize all dependencies.

        Note: Telegram service uses parameterized cached instances,
        so no global initialization is needed.
        """
        logger.info("Initializing dependencies...")
        logger.info(
            "Telegram service uses per-request cached instances (no explicit init)."
        )
        logger.info("Dependencies initialized successfully.")

    @classmethod
    async def shutdown(cls) -> None:
        """
        Shut down all dependencies gracefully.

        Note: Telegram service instances are managed by lru_cache,
        so no explicit cleanup is needed.
        """
        logger.info("Shutting down dependencies...")
        logger.info(
            "Telegram service instances managed by lru_cache (no explicit cleanup)."
        )
        logger.info("Dependencies shut down successfully.")

    @classmethod
    def get_telegram_service(cls, token: str, channel: str) -> _TelegramService:
        """
        Get a TelegramService instance configured for the specified token and channel.

        This method uses the cached service factory from the telegram module,
        ensuring that services with the same token/channel combination are reused.

        Args:
            token: The Telegram bot API token
            channel: The Telegram channel ID

        Returns:
            Cached TelegramService instance
        """
        return create_telegram_service(token=token, channel=channel)


# Alias the class method for use as FastAPI dependency
get_telegram_service = DependencyContainer.get_telegram_service
