import logging

from mcp_server_hangman.hangman.module import HangmanService
from mcp_server_hangman.hangman.module import get_hangman_service as create_hangman_service

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
        async def endpoint(hangman_service: HangmanService = Depends(get_hangman_service)):
            ...
    """

    _hangman_service: HangmanService | None = None

    @classmethod
    def initialize(cls) -> None:
        """
        Initialize all dependencies.

        Call this once during application startup (in lifespan).
        """
        logger.info("Initializing dependencies...")

        cls._hangman_service = create_hangman_service()

        logger.info("Dependencies initialized successfully.")

    @classmethod
    async def shutdown(cls) -> None:
        """
        Shut down all dependencies gracefully.

        Call this once during application shutdown (in lifespan).
        """
        logger.info("Shutting down dependencies...")

        cls._hangman_service = None

        logger.info("Dependencies shut down successfully.")

    @classmethod
    def get_hangman_service(cls) -> HangmanService:
        """
        Get the HangmanService instance.

        Usage as FastAPI dependency:
            @router.post("/game")
            async def game(hangman_service: HangmanService = Depends(get_hangman_service)):
                ...
        """
        if cls._hangman_service is None:
            raise RuntimeError(
                "DependencyContainer not initialized. Call DependencyContainer.initialize() first."
            )
        return cls._hangman_service


# Alias the class method for use as FastAPI dependency
get_hangman_service = DependencyContainer.get_hangman_service
