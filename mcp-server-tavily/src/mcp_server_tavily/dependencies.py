import logging

from mcp_server_tavily.tavily import _TavilyService
from mcp_server_tavily.tavily import \
    get_tavily_service as create_tavily_service

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
        async def endpoint(tavily_service: _TavilyService = Depends(get_tavily_service)):
            ...
    """

    _tavily_service: _TavilyService | None = None

    @classmethod
    def initialize(cls) -> None:
        """
        Initialize all dependencies.

        Call this once during application startup (in lifespan).
        """
        logger.info("Initializing dependencies...")

        cls._tavily_service = create_tavily_service()

        logger.info("Dependencies initialized successfully.")

    @classmethod
    async def shutdown(cls) -> None:
        """
        Shut down all dependencies gracefully.

        Call this once during application shutdown (in lifespan).
        """
        logger.info("Shutting down dependencies...")

        cls._tavily_service = None

        logger.info("Dependencies shut down successfully.")

    @classmethod
    def get_tavily_service(cls) -> _TavilyService:
        """
        Get the TavilyService instance.

        Usage as FastAPI dependency:
            @router.post("/search")
            async def search(tavily_service: _TavilyService = Depends(get_tavily_service)):
                ...
        """
        if cls._tavily_service is None:
            raise RuntimeError(
                "DependencyContainer not initialized. Call DependencyContainer.initialize() first."
            )
        return cls._tavily_service


# Alias the class method for use as FastAPI dependency
get_tavily_service = DependencyContainer.get_tavily_service
