"""
FastAPI dependency injection for the Cartesia MCP Server.

Main responsibility: Provide dependency injection functions for shared resources.
"""

import logging

from mcp_server_cartesia.cartesia_client import (
    _CartesiaService,
    get_cartesia_service as create_cartesia_service,
)

logger = logging.getLogger(__name__)


class DependencyContainer:
    """
    Centralized container for all application dependencies.

    Usage:
        # In app.py lifespan:
        DependencyContainer.initialize()
        yield
        await DependencyContainer.shutdown()

        # In route handlers via Depends():
        @router.post("/endpoint")
        async def endpoint(cartesia_service: _CartesiaService = Depends(get_cartesia_service)):
            ...
    """

    _cartesia_service: _CartesiaService | None = None

    @classmethod
    def initialize(cls) -> None:
        """
        Initialize all dependencies.

        Call this once during application startup (in lifespan).
        """
        logger.info("Initializing dependencies...")

        cls._cartesia_service = create_cartesia_service()

        logger.info("Dependencies initialized successfully.")

    @classmethod
    async def shutdown(cls) -> None:
        """
        Shut down all dependencies gracefully.

        Call this once during application shutdown (in lifespan).
        """
        logger.info("Shutting down dependencies...")

        cls._cartesia_service = None

        logger.info("Dependencies shut down successfully.")

    @classmethod
    def get_cartesia_service(cls) -> _CartesiaService:
        """
        Get the CartesiaService instance.

        Usage as FastAPI dependency:
            @router.post("/generate-tts")
            async def generate_tts(cartesia_service: _CartesiaService = Depends(get_cartesia_service)):
                ...
        """
        if cls._cartesia_service is None:
            raise RuntimeError(
                "DependencyContainer not initialized. Call DependencyContainer.initialize() first."
            )
        return cls._cartesia_service


# Alias the class method for use as FastAPI dependency
get_cartesia_service = DependencyContainer.get_cartesia_service
