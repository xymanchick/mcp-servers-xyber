# This file should change to fit your business logic needs
# It contains custom error classes and configuration models

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

# --- Custom Error Classes --- #


class WeatherError(Exception):
    """Base class for weather-related errors."""

    pass


class WeatherApiError(WeatherError):
    """Raised when OpenWeatherMap API returns an error."""

    pass


class WeatherConfigError(WeatherError):
    """Raised when there's an issue with configuration."""

    pass


class WeatherClientError(WeatherError):
    """Raised when there's an issue with the weather client."""

    pass


# --- Configuration Model --- #


class WeatherConfig(BaseSettings):
    """Configuration for the Weather service.

    Attributes:
        api_key: OpenWeatherMap API key (required)
        timeout_seconds: Timeout for API requests in seconds
        enable_caching: Whether to enable caching of weather responses
        cache_ttl_seconds: Cache time-to-live in seconds
    """

    # Pydantic Settings configuration
    model_config = SettingsConfigDict(
        env_prefix="WEATHER_",  # Look for env vars like WEATHER_API_KEY
        env_file=".env",  # Load from .env file if it exists
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore extra fields from the environment
        case_sensitive=False,  # Environment variables are case-insensitive
    )

    api_key: str
    timeout_seconds: int = 10
    enable_caching: bool = True
    cache_ttl_seconds: int = 300  # 5 minutes


@lru_cache(maxsize=1)
def get_weather_config() -> WeatherConfig:
    """Get a cached instance of WeatherConfig.

    Returns:
        Validated WeatherConfig instance

    Raises:
        WeatherConfigError: If configuration validation fails
    """
    config = WeatherConfig()
    return config
