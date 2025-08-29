import json
import pytest
import aiohttp
import tenacity
from unittest.mock import Mock

from mcp_server_weather.weather.config import WeatherConfig, WeatherApiError, WeatherClientError

from mcp_server_weather.weather.models import WeatherData
from mcp_server_weather.weather.module import WeatherClient


@pytest.fixture
def mock_weather_config():
    """Mock weather configuration for testing."""
    config = Mock(spec=WeatherConfig)
    config.api_key = "test_api_key_123"
    config.default_city = "London"
    config.default_latitude = "51.5074"
    config.default_longitude = "-0.1278"
    config.units = "metric"
    config.timeout_seconds = 5
    config.enable_caching = True
    config.cache_ttl_seconds = 300
    return config


@pytest.fixture
def mock_weather_config_no_cache():
    """Mock weather configuration for testing with caching disabled."""
    config = Mock(spec=WeatherConfig)
    config.api_key = "test_api_key"
    config.timeout_seconds = 5
    config.enable_caching = False  # Disable caching for retry tests
    config.cache_ttl_seconds = 300
    return config


@pytest.fixture
def weather_client(mock_weather_config_no_cache):
    """Create WeatherClient instance for testing (with caching disabled)."""
    client = WeatherClient(mock_weather_config_no_cache)
    return client


@pytest.fixture
def weather_client_with_cache(mock_weather_config):
    """Create WeatherClient instance for testing (with caching enabled)."""
    client = WeatherClient(mock_weather_config)
    return client


@pytest.fixture
def mock_asyncio_sleep():
    """Mock asyncio.sleep to make retry tests fast."""
    async def mock_sleep(seconds):
        pass  # Don't actually sleep
    return mock_sleep


@pytest.fixture
def mock_http_response_factory():
    """Factory for creating mock HTTP responses."""
    def create_response(status=200, json_data=None, text_data=""):
        class MockResponse:
            def __init__(self):
                self.status = status
            
            async def json(self):
                return json_data or {}
            
            async def text(self):
                return text_data
            
            async def __aenter__(self):
                return self
            
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass
        
        return MockResponse()
    
    return create_response


@pytest.fixture
def sample_weather_api_response():
    """Sample OpenWeatherMap API response."""
    return {
        "coord": {"lon": -0.1278, "lat": 51.5074},
        "weather": [
            {"id": 800, "main": "Clear", "description": "clear sky", "icon": "01d"}
        ],
        "base": "stations",
        "main": {
            "temp": 15.5,
            "feels_like": 14.8,
            "temp_min": 14.2,
            "temp_max": 16.7,
            "pressure": 1012,
            "humidity": 76,
        },
        "visibility": 10000,
        "wind": {"speed": 3.6, "deg": 250},
        "clouds": {"all": 0},
        "dt": 1621152000,
        "sys": {
            "type": 2,
            "id": 2019646,
            "country": "GB",
            "sunrise": 1621137540,
            "sunset": 1621193088,
        },
        "timezone": 3600,
        "id": 2643743,
        "name": "London",
        "cod": 200,
    }


@pytest.fixture
def sample_weather_data():
    """Sample WeatherData instance for testing."""
    return WeatherData(state="clear sky", temperature="15.5C", humidity="76%")


@pytest.fixture
def sample_weather_data_imperial():
    """Sample WeatherData instance for imperial units testing."""
    return WeatherData(
        state="clear sky",
        temperature="59.9F",
        humidity="76%"
    )


@pytest.fixture
def sample_error_api_response():
    """Sample error response from OpenWeatherMap API."""
    return {
        "cod": 401,
        "message": "Invalid API key. Please see http://openweathermap.org/faq#error401 for more info."
    }


@pytest.fixture
def sample_incomplete_api_response():
    """Sample incomplete API response that should cause parsing errors."""
    return {
        "cod": 200,
        "weather": [],  # Empty weather array will cause KeyError
        "main": {
            "temp": 15.5,
            "humidity": 76
        }
    }


@pytest.fixture
def mock_response():
    """Mock requests.Response object."""

    class MockResponse:
        def __init__(self, json_data, status_code):
            self.json_data = json_data
            self.status_code = status_code
            self.text = json.dumps(json_data)

        def json(self):
            return self.json_data

        def raise_for_status(self):
            if self.status_code != 200:
                from requests.exceptions import HTTPError

                raise HTTPError(f"HTTP Error: {self.status_code}")    
    return MockResponse


@pytest.fixture
def weather_client_class():
    """Fixture that provides standard WeatherClient for most tests."""
    return WeatherClient


@pytest.fixture
def fast_weather_client():
    """Fixture that provides WeatherClient with fast retry for performance tests."""
    from mcp_server_weather.weather.module import logger
    
    def _create_client(config):
        class FastWeatherClient(WeatherClient):
            def __init__(self, config):
                super().__init__(config)
                
            @tenacity.retry(
                stop=tenacity.stop_after_attempt(3),
                wait=tenacity.wait_fixed(0.01),
                retry=tenacity.retry_if_exception_type((aiohttp.ClientError, WeatherApiError))
            )
            async def get_weather(self, latitude: str, longitude: str, units: str):
                """Fast version of get_weather with minimal retry delay."""
                # Implementation copied from WeatherClient.get_weather without the original decorator
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
        
        return FastWeatherClient(config)
    
    return _create_client
