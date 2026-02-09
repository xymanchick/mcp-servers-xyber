import logging

from mcp_server_qdrant.qdrant import QdrantConnector
from mcp_server_qdrant.qdrant.config import (EmbeddingProviderSettings,
                                             QdrantConfig)
from mcp_server_qdrant.qdrant.embeddings.factory import \
    create_embedding_provider

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
        async def endpoint(connector: QdrantConnector = Depends(get_qdrant_connector)):
            ...
    """

    _qdrant_connector: QdrantConnector | None = None

    @classmethod
    def initialize(cls) -> None:
        """
        Initialize all dependencies.

        Call this once during application startup (in lifespan).
        """
        logger.info("Initializing dependencies...")

        config = QdrantConfig()
        embedding_provider_settings = EmbeddingProviderSettings()
        embedding_provider = create_embedding_provider(embedding_provider_settings)
        cls._qdrant_connector = QdrantConnector(config, embedding_provider)

        logger.info("Dependencies initialized successfully.")

    @classmethod
    async def shutdown(cls) -> None:
        """
        Shut down all dependencies gracefully.

        Call this once during application shutdown (in lifespan).
        """
        logger.info("Shutting down dependencies...")

        cls._qdrant_connector = None

        logger.info("Dependencies shut down successfully.")

    @classmethod
    def get_qdrant_connector(cls) -> QdrantConnector:
        """
        Get the QdrantConnector instance.

        Usage as FastAPI dependency:
            @router.post("/store")
            async def store(connector: QdrantConnector = Depends(get_qdrant_connector)):
                ...
        """
        if cls._qdrant_connector is None:
            raise RuntimeError(
                "DependencyContainer not initialized. Call DependencyContainer.initialize() first."
            )
        return cls._qdrant_connector


# Alias the class method for use as FastAPI dependency
get_qdrant_connector = DependencyContainer.get_qdrant_connector
