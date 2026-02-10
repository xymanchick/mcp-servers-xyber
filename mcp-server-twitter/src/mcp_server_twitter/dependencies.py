import logging

from mcp_server_twitter.twitter import AsyncTwitterClient, get_twitter_client

logger = logging.getLogger(__name__)


class DependencyContainer:
    """
    Centralized container for all application dependencies.

    Usage:
        # In app.py lifespan:
        await DependencyContainer.initialize()

    Yield:
        await DependencyContainer.shutdown()

        # In route handlers via Depends():
        @router.post("/endpoint")
        async def endpoint(client: AsyncTwitterClient = Depends(get_twitter_client_dep)):
            ...

    """

    _twitter_client: AsyncTwitterClient | None = None

    @classmethod
    async def initialize(cls) -> None:
        """
        Initialize all dependencies.

        Call this once during application startup (in lifespan).
        """
        logger.info("Initializing dependencies...")

        cls._twitter_client = await get_twitter_client()

        logger.info("Dependencies initialized successfully.")

    @classmethod
    async def shutdown(cls) -> None:
        """
        Shut down all dependencies gracefully.

        Call this once during application shutdown (in lifespan).
        """
        logger.info("Shutting down dependencies...")

        # Twitter client doesn't have explicit close method currently
        cls._twitter_client = None

        logger.info("Dependencies shut down successfully.")

    @classmethod
    def get_twitter_client(cls) -> AsyncTwitterClient:
        """
        Get the AsyncTwitterClient instance.

        Usage as FastAPI dependency:
            @router.post("/tweet")
            async def create_tweet(client: AsyncTwitterClient = Depends(get_twitter_client_dep)):
                ...
        """
        if cls._twitter_client is None:
            raise RuntimeError(
                "DependencyContainer not initialized. Call DependencyContainer.initialize() first."
            )
        return cls._twitter_client


# Alias the class method for use as FastAPI dependency
get_twitter_client_dep = DependencyContainer.get_twitter_client
