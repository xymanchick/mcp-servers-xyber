import logging

from mcp_server_arxiv.xy_arxiv import _ArxivService
from mcp_server_arxiv.xy_arxiv import get_arxiv_service as create_arxiv_service

logger = logging.getLogger(__name__)


class DependencyContainer:
    """
    Centralized container for all application dependencies.

    Usage:
        # In app.py lifespan:
        DependencyContainer.initialize()

    Yield:
        await DependencyContainer.shutdown()

        # In route handlers via Depends():
        @router.post("/endpoint")
        async def endpoint(arxiv_service: _ArxivService = Depends(get_arxiv_service)):
            ...

    """

    _arxiv_service: _ArxivService | None = None

    @classmethod
    def initialize(cls) -> None:
        """
        Initialize all dependencies.

        Call this once during application startup (in lifespan).
        """
        logger.info("Initializing dependencies...")

        cls._arxiv_service = create_arxiv_service()

        logger.info("Dependencies initialized successfully.")

    @classmethod
    async def shutdown(cls) -> None:
        """
        Shut down all dependencies gracefully.

        Call this once during application shutdown (in lifespan).
        """
        logger.info("Shutting down dependencies...")

        cls._arxiv_service = None

        logger.info("Dependencies shut down successfully.")

    @classmethod
    def get_arxiv_service(cls) -> _ArxivService:
        """
        Get the ArxivService instance.

        Usage as FastAPI dependency:
            @router.post("/search")
            async def search(arxiv_service: _ArxivService = Depends(get_arxiv_service)):
                ...
        """
        if cls._arxiv_service is None:
            raise RuntimeError(
                "DependencyContainer not initialized. Call DependencyContainer.initialize() first."
            )
        return cls._arxiv_service


# Alias the class method for use as FastAPI dependency
get_arxiv_service = DependencyContainer.get_arxiv_service
