"""
FastAPI dependencies for YouTube service.
"""

import logging

from mcp_server_youtube.youtube import YouTubeVideoSearchAndTranscript
from mcp_server_youtube.youtube import get_youtube_client as create_youtube_client
from mcp_server_youtube.youtube.methods import DatabaseManager
from mcp_server_youtube.youtube.methods import get_db_manager as create_db_manager

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
        async def endpoint(youtube_service: YouTubeVideoSearchAndTranscript = Depends(get_youtube_service)):
            ...

    """

    _youtube_service: YouTubeVideoSearchAndTranscript | None = None
    _db_manager: DatabaseManager | None = None

    @classmethod
    def initialize(cls) -> None:
        """
        Initialize all dependencies.

        Call this once during application startup (in lifespan).
        """
        logger.info("Initializing dependencies...")

        cls._youtube_service = create_youtube_client()
        logger.info("YouTube service initialized successfully.")

        try:
            cls._db_manager = create_db_manager()
            logger.info("Database manager initialized successfully.")
        except Exception as e:
            logger.warning(
                "Database initialization failed; caching disabled. Error: %s", e
            )
            cls._db_manager = None

        logger.info("Dependencies initialized successfully.")

    @classmethod
    async def shutdown(cls) -> None:
        """
        Shut down all dependencies gracefully.

        Call this once during application shutdown (in lifespan).
        """
        logger.info("Shutting down dependencies...")

        cls._youtube_service = None
        cls._db_manager = None

        logger.info("Dependencies shut down successfully.")

    @classmethod
    def get_youtube_service(cls) -> YouTubeVideoSearchAndTranscript:
        """
        Get the YouTubeVideoSearchAndTranscript instance.

        Usage as FastAPI dependency:
            @router.post("/search")
            async def search(youtube_service: YouTubeVideoSearchAndTranscript = Depends(get_youtube_service)):
                ...
        """
        if cls._youtube_service is None:
            raise RuntimeError(
                "DependencyContainer not initialized. Call DependencyContainer.initialize() first."
            )
        return cls._youtube_service

    @classmethod
    def get_db_manager(cls) -> DatabaseManager | None:
        """
        Get the DatabaseManager instance.

        Returns None if database is not available.

        Usage as FastAPI dependency:
            @router.get("/videos")
            async def get_videos(db: DatabaseManager = Depends(get_db_manager)):
                ...
        """
        # Note: db_manager can be None if database is unavailable
        return cls._db_manager


# Alias the class methods for use as FastAPI dependencies
get_youtube_service = DependencyContainer.get_youtube_service
get_youtube_service_search_only = (
    DependencyContainer.get_youtube_service
)  # Same as get_youtube_service
get_db_manager = DependencyContainer.get_db_manager
