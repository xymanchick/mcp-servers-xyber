import logging

from mcp_server_aave.aave import AaveClient, AaveConfig, get_aave_config

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
        async def endpoint(client: AaveClient = Depends(get_aave_client)):
            ...

    """

    _aave_client: AaveClient | None = None

    @classmethod
    def initialize(cls) -> None:
        """
        Initialize all dependencies.

        Call this once during application startup (in lifespan).
        """
        logger.info("Initializing dependencies...")

        config: AaveConfig = get_aave_config()
        cls._aave_client = AaveClient(config)

        logger.info("Dependencies initialized successfully.")

    @classmethod
    async def shutdown(cls) -> None:
        """
        Shut down all dependencies gracefully.

        Call this once during application shutdown (in lifespan).
        """
        logger.info("Shutting down dependencies...")

        if cls._aave_client:
            await cls._aave_client.close()
            cls._aave_client = None

        logger.info("Dependencies shut down successfully.")

    @classmethod
    def get_aave_client(cls) -> AaveClient:
        """
        Get the AaveClient instance.

        Usage as FastAPI dependency:
            @router.get("/reserves")
            async def get_reserves(client: AaveClient = Depends(get_aave_client)):
                ...
        """
        if cls._aave_client is None:
            raise RuntimeError(
                "DependencyContainer not initialized. Call DependencyContainer.initialize() first."
            )
        return cls._aave_client


# Alias the class method for use as FastAPI dependency
get_aave_client = DependencyContainer.get_aave_client
