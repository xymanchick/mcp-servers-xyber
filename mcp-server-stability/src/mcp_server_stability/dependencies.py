import logging

from mcp_server_stability.stable_diffusion import (StabilityService,
                                                   StableDiffusionClientConfig)

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
        async def endpoint(service: StabilityService = Depends(get_stability_service)):
            ...
    """

    _stability_service: StabilityService | None = None

    @classmethod
    async def initialize(cls) -> None:
        """
        Initialize all dependencies.

        Call this once during application startup (in lifespan).
        """
        logger.info("Initializing dependencies...")

        config = StableDiffusionClientConfig()
        cls._stability_service = StabilityService(config)

        logger.info("Dependencies initialized successfully.")

    @classmethod
    async def shutdown(cls) -> None:
        """
        Shut down all dependencies gracefully.

        Call this once during application shutdown (in lifespan).
        """
        logger.info("Shutting down dependencies...")

        if cls._stability_service:
            await cls._stability_service.cleanup()
            cls._stability_service = None

        logger.info("Dependencies shut down successfully.")

    @classmethod
    def get_stability_service(cls) -> StabilityService:
        """
        Get the StabilityService instance.

        Usage as FastAPI dependency:
            @router.post("/generate")
            async def generate(service: StabilityService = Depends(get_stability_service)):
                ...
        """
        if cls._stability_service is None:
            raise RuntimeError(
                "DependencyContainer not initialized. Call DependencyContainer.initialize() first."
            )
        return cls._stability_service


# Alias the class method for use as FastAPI dependency
get_stability_service = DependencyContainer.get_stability_service
