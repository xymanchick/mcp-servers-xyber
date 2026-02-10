import logging

from mcp_server_wikipedia.wikipedia import (_WikipediaService,
                                            get_wikipedia_service)

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
        async def endpoint(service: _WikipediaService = Depends(get_wiki_service)):
            ...
    """

    _wiki_service: _WikipediaService | None = None

    @classmethod
    def initialize(cls) -> None:
        """
        Initialize all dependencies.

        Call this once during application startup (in lifespan).
        """
        logger.info("Initializing dependencies...")

        cls._wiki_service = get_wikipedia_service()

        logger.info("Dependencies initialized successfully.")

    @classmethod
    async def shutdown(cls) -> None:
        """
        Shut down all dependencies gracefully.

        Call this once during application shutdown (in lifespan).
        """
        logger.info("Shutting down dependencies...")

        cls._wiki_service = None

        logger.info("Dependencies shut down successfully.")

    @classmethod
    def get_wiki_service(cls) -> _WikipediaService:
        """
        Get the _WikipediaService instance.

        Usage as FastAPI dependency:
            @router.get("/search")
            async def search(service: _WikipediaService = Depends(get_wiki_service)):
                ...
        """
        if cls._wiki_service is None:
            raise RuntimeError(
                "DependencyContainer not initialized. Call DependencyContainer.initialize() first."
            )
        return cls._wiki_service


# Alias the class method for use as FastAPI dependency
get_wiki_service = DependencyContainer.get_wiki_service
