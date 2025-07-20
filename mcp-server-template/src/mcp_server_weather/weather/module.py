# This file should change to fit your business logic needs
# It contains the core logic of the module, implementing abstractions
# defined in the __init__.py file

from __future__ import annotations

import logging
import time
from functools import lru_cache
from typing import Any, Literal

import aiohttp
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

from mcp_server_weather.weather.config import (
    WeatherConfig,
    WeatherApiError,
    WeatherClientError,
    get_weather_config,
)
from mcp_server_weather.weather.models import WeatherData

# --- Logger Setup --- #

# It's good practice to have a module-level logger.
# The actual configuration (level, handlers) is usually done in the main application entry point.
logger = logging.getLogger(__name__)

# --- Setup Retry Decorators --- #
retry_api_call = retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=0.5, max=10),
    retry=retry_if_exception_type((aiohttp.ClientError, WeatherApiError)),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)


@lru_cache(maxsize=1)
def get_weather_client() -> WeatherClient:
    """Get a cached instance of WeatherClient.
    
    Returns:
        Initialized WeatherClient instance
        
    Raises:
        WeatherConfigError: If configuration validation fails
    """
    config = get_weather_config()
    return WeatherClient(config)


class WeatherClient:
    """Weather client for fetching weather data from OpenWeatherMap API.
    
    Handles interaction with the OpenWeatherMap API with retry logic and caching.
    """
    
    API_BASE_URL = "https://api.openweathermap.org/data/2.5/weather"
    
    def __init__(self, config: WeatherConfig) -> None:
        """Initialize the WeatherClient.
        
        Args:
            config: Weather configuration settings
            
        Raises:
            WeatherConfigError: If configuration validation fails
        """
        self.config = config
        self._cache: dict[str, tuple[float, WeatherData]] = {}
        self._session: aiohttp.ClientSession | None = None
        logger.info("WeatherClient initialized")
        
    async def _ensure_session(self) -> aiohttp.ClientSession:
        """Ensure HTTP session exists.
        
        Returns:
            Active aiohttp ClientSession
        """
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds)
            )
        return self._session
        
    def _build_request_params(
        self, 
        latitude: str,
        longitude: str,
        units: Literal['metric', 'imperial']
    ) -> dict[str, str]:
        """Build request parameters for OpenWeatherMap API.
        
        Args:
            latitude: Optional latitude override
            longitude: Optional longitude override
            
        Returns:
            Dictionary of request parameters
        """
        return {
            "lat": latitude,
            "lon": longitude,
            "units": units,
            "appid": self.config.api_key,
        }
        
    def _get_cache_key(self, latitude: str, longitude: str, units: Literal['metric', 'imperial']) -> str:
        """Generate cache key for a location.
        
        Args:
            latitude: Location latitude
            longitude: Location longitude
            
        Returns:
            Cache key string
        """
        return f"{latitude}:{longitude}:{units}"
        
    def _get_from_cache(self, cache_key: str) -> WeatherData | None:
        """Try to get weather data from cache.
        
        Args:
            cache_key: Cache key for the location
            
        Returns:
            WeatherData if found and not expired, None otherwise
        """
        if not self.config.enable_caching:
            return None
            
        if cache_key not in self._cache:
            return None
            
        timestamp, data = self._cache[cache_key]
        if time.time() - timestamp > self.config.cache_ttl_seconds:
            # Cache expired
            del self._cache[cache_key]
            return None
            
        logger.debug(f"Cache hit for {cache_key}")
        return data
        
    def _store_in_cache(self, cache_key: str, data: WeatherData) -> None:
        """Store weather data in cache.
        
        Args:
            cache_key: Cache key for the location
            data: Weather data to cache
        """
        if not self.config.enable_caching:
            return
            
        self._cache[cache_key] = (time.time(), data)
        logger.debug(f"Stored in cache: {cache_key}")
        
    async def close(self) -> None:
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    @retry_api_call
    async def get_weather(
        self, 
        latitude: str,
        longitude: str,
        units: Literal['metric', 'imperial'] = 'metric'
    ) -> WeatherData:
        """Get weather data for a location.
        
        Args:
            latitude: Optional latitude override
            longitude: Optional longitude override
            
        Returns:
            WeatherData object with current weather information
            
        Raises:
            WeatherApiError: If the API request fails
            WeatherClientError: For other unexpected errors
        """
        # Use provided coordinates 
        lat = latitude 
        lon = longitude
        
        # Try to get from cache first
        cache_key = self._get_cache_key(lat, lon, units)
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            return cached_data
        
        # Build request parameters
        params = self._build_request_params(lat, lon, units)
        
        try:
            logger.info(f"Fetching weather data for coordinates: {lat}, {lon}")
            session = await self._ensure_session()
            
            async with session.get(self.API_BASE_URL, params=params) as response:
                # Check for HTTP errors
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"HTTP error {response.status}: {error_text}")
                    raise WeatherApiError(f"OpenWeatherMap API HTTP error: {response.status}")
                
                # Parse JSON response
                data = await response.json()
                
                # Check for API error responses
                if "cod" in data and data["cod"] != 200:
                    error_msg = data.get("message", "Unknown API error")
                    logger.error(f"API error: {error_msg}")
                    raise WeatherApiError(f"OpenWeatherMap API error: {error_msg}")
                
                # Create WeatherData object
                weather_data = WeatherData.from_api_response(data)
                
                # Store in cache
                self._store_in_cache(cache_key, weather_data)
                
                logger.info(f"Successfully retrieved weather data: {weather_data}")
                return weather_data
            
        except WeatherApiError:
            # Re-raise WeatherApiError as-is
            raise
            
        except aiohttp.ClientError as e:
            logger.error(f"Request error: {e}")
            raise WeatherApiError(f"Failed to connect to OpenWeatherMap API: {e}") from e
            
        except (KeyError, IndexError) as e:
            logger.error(f"Data parsing error: {e}")
            raise WeatherClientError(f"Failed to parse weather data: {e}") from e
            
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            raise WeatherClientError(f"Unexpected error getting weather data: {e}") from e
