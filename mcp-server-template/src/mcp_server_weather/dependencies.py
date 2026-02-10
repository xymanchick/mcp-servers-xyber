"""
This module should be changed to include your server's dependencies like API clients, database session managers, etc.

Main responsibility: Provide a single place to initialize, access, and shut down
all service clients used by the application.
"""

import logging

from mcp_server_weather.weather import WeatherClient, WeatherConfig, get_weather_config

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
        async def endpoint(client: WeatherClient = Depends(get_weather_client)):
            ...

    """

    _weather_client: WeatherClient | None = None

    @classmethod
    def initialize(cls) -> None:
        """
        Initialize all dependencies.

        Call this once during application startup (in lifespan).
        """
        logger.info("Initializing dependencies...")

        config: WeatherConfig = get_weather_config()
        cls._weather_client = WeatherClient(config)

        logger.info("Dependencies initialized successfully.")

    @classmethod
    async def shutdown(cls) -> None:
        """
        Shut down all dependencies gracefully.

        Call this once during application shutdown (in lifespan).
        """
        logger.info("Shutting down dependencies...")

        if cls._weather_client:
            await cls._weather_client.close()
            cls._weather_client = None

        logger.info("Dependencies shut down successfully.")

    @classmethod
    def get_weather_client(cls) -> WeatherClient:
        """
        Get the WeatherClient instance.

        Usage as FastAPI dependency:
            @router.get("/weather")
            async def get_weather(client: WeatherClient = Depends(get_weather_client)):
                ...
        """
        if cls._weather_client is None:
            raise RuntimeError(
                "DependencyContainer not initialized. Call DependencyContainer.initialize() first."
            )
        return cls._weather_client


# Alias the class method for use as FastAPI dependency
get_weather_client = DependencyContainer.get_weather_client
