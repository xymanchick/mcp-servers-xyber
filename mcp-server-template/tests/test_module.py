"""Test cases for WeatherClient module."""


import json
import time
from unittest.mock import MagicMock, Mock, patch

import aiohttp
import pytest
from aioresponses import aioresponses

from tenacity import RetryError

from mcp_server_weather.weather.module import WeatherClient, get_weather_client


from mcp_server_weather.weather.config import (
    WeatherApiError,
    WeatherClientError,
    WeatherConfigError,
    get_weather_config,
)
from mcp_server_weather.weather.models import WeatherData
from mcp_server_weather.weather.module import WeatherClient, get_weather_client


# Fast retry decorator for testing
@pytest.fixture
def fast_retry_decorator():
    """Fast retry decorator for testing."""
    from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type, before_sleep_log
    import logging
    
    return retry(
        stop=stop_after_attempt(3),  # Reduced from 5 to 3
        wait=wait_fixed(0.01),       # Very short wait instead of exponential
        retry=retry_if_exception_type((aiohttp.ClientError, WeatherApiError)),
        before_sleep=before_sleep_log(logging.getLogger(__name__), logging.WARNING),
        reraise=True,
    )


class TestWeatherClient:
    """Test cases for WeatherClient class."""

    def test_init_success(self, mock_weather_config):
        """Test successful WeatherClient initialization."""
        client = WeatherClient(mock_weather_config)

        assert client.config == mock_weather_config
        assert client._cache == {}
        assert client._session is None
        assert client.API_BASE_URL == "https://api.openweathermap.org/data/2.5/weather"

    def test_build_request_params_default(self, mock_weather_config):
        """Test building request parameters with default values."""
        client = WeatherClient(mock_weather_config)
        params = client._build_request_params(
            latitude=mock_weather_config.default_latitude,
            longitude=mock_weather_config.default_longitude,
            units=mock_weather_config.units,
        )

        assert params == {
            "lat": mock_weather_config.default_latitude,
            "lon": mock_weather_config.default_longitude,
            "units": mock_weather_config.units,
            "appid": mock_weather_config.api_key,
        }

    def test_build_request_params_custom(self, mock_weather_config):
        """Test building request parameters with custom values."""
        client = WeatherClient(mock_weather_config)
        params = client._build_request_params(
            latitude="40.7128", longitude="-74.0060", units="imperial"
        )

        assert params == {
            "lat": "40.7128",
            "lon": "-74.0060",
            "units": "imperial",
            "appid": mock_weather_config.api_key,
        }

    def test_cache_key_generation(self, mock_weather_config):
        """Test cache key generation."""
        client = WeatherClient(mock_weather_config)
        key = client._get_cache_key("40.7128", "-74.0060", "metric")

        assert key == "40.7128:-74.0060:metric"

        # Test with different units
        mock_weather_config.units = "imperial"
        client = WeatherClient(mock_weather_config)
        key = client._get_cache_key("40.7128", "-74.0060", "imperial")

        assert key == "40.7128:-74.0060:imperial"

    def test_get_from_cache_disabled(self, mock_weather_config, sample_weather_data):
        """Test cache retrieval when caching is disabled."""
        mock_weather_config.enable_caching = False
        client = WeatherClient(mock_weather_config)

        # Add item to cache (shouldn't be retrieved)
        cache_key = "test-key"
        client._cache[cache_key] = (time.time(), sample_weather_data)

        result = client._get_from_cache(cache_key)
        assert result is None

    def test_get_from_cache_miss(self, mock_weather_config):
        """Test cache miss."""
        client = WeatherClient(mock_weather_config)
        result = client._get_from_cache("nonexistent-key")
        assert result is None

    def test_get_from_cache_expired(self, mock_weather_config, sample_weather_data):
        """Test expired cache item."""
        client = WeatherClient(mock_weather_config)

        # Add expired item to cache
        cache_key = "expired-key"
        client._cache[cache_key] = (
            time.time() - 600,
            sample_weather_data,
        )  # 10 minutes old

        result = client._get_from_cache(cache_key)
        assert result is None
        assert cache_key not in client._cache  # Should be removed

    def test_get_from_cache_hit(self, mock_weather_config, sample_weather_data):
        """Test successful cache hit."""
        client = WeatherClient(mock_weather_config)

        # Add fresh item to cache
        cache_key = "fresh-key"
        client._cache[cache_key] = (time.time(), sample_weather_data)

        result = client._get_from_cache(cache_key)
        assert result == sample_weather_data

    def test_store_in_cache_disabled(self, mock_weather_config, sample_weather_data):
        """Test storing in cache when caching is disabled."""
        mock_weather_config.enable_caching = False
        client = WeatherClient(mock_weather_config)

        client._store_in_cache("test-key", sample_weather_data)
        assert len(client._cache) == 0

    def test_store_in_cache_enabled(self, mock_weather_config, sample_weather_data):
        """Test storing in cache when caching is enabled."""
        client = WeatherClient(mock_weather_config)

        cache_key = "test-key"
        client._store_in_cache(cache_key, sample_weather_data)

        assert cache_key in client._cache
        assert client._cache[cache_key][1] == sample_weather_data

    @pytest.mark.asyncio
    async def test_ensure_session(self, mock_weather_config):
        """Test session initialization."""
        client = WeatherClient(mock_weather_config)

        # Initially no session
        assert client._session is None

        # Get session
        session = await client._ensure_session()
        assert isinstance(session, aiohttp.ClientSession)
        assert client._session is session

        # Get session again (should be same instance)
        session2 = await client._ensure_session()
        assert session2 is session

        # Clean up
        await client.close()

    @pytest.mark.asyncio
    async def test_close_session(self, mock_weather_config):
        """Test closing the session."""
        client = WeatherClient(mock_weather_config)

        # Create session
        session = await client._ensure_session()
        assert not session.closed

        # Close session
        await client.close()
        assert session.closed
        assert client._session is None

        # Close when no session exists (should not raise)
        await client.close()

    @pytest.mark.asyncio
    async def test_get_weather_success(
        self, mock_weather_config, sample_weather_api_response
    ):
        """Test successful weather retrieval."""
        client = WeatherClient(mock_weather_config)

        with aioresponses() as mocked:
            # Mock the API response
            url = f"{client.API_BASE_URL}?lat={mock_weather_config.default_latitude}&lon={mock_weather_config.default_longitude}&units={mock_weather_config.units}&appid={mock_weather_config.api_key}"
            mocked.get(url, status=200, payload=sample_weather_api_response)

            result = await client.get_weather(
                latitude=mock_weather_config.default_latitude,
                longitude=mock_weather_config.default_longitude,
                units=mock_weather_config.units,
            )

            assert isinstance(result, WeatherData)
            assert result.state == "clear sky"
            assert result.temperature == "15.5C"
            assert result.humidity == "76%"

        # Clean up
        await client.close()

    @pytest.mark.asyncio
    async def test_get_weather_from_cache(
        self, mock_weather_config, sample_weather_data
    ):
        """Test retrieving weather from cache."""
        client = WeatherClient(mock_weather_config)

        # Add item to cache
        cache_key = client._get_cache_key(
            mock_weather_config.default_latitude,
            mock_weather_config.default_longitude,
            mock_weather_config.units,
        )
        client._cache[cache_key] = (time.time(), sample_weather_data)

        with aioresponses() as mocked:
            # API should not be called
            result = await client.get_weather(
                latitude=mock_weather_config.default_latitude,
                longitude=mock_weather_config.default_longitude,
                units=mock_weather_config.units,
            )

            assert result == sample_weather_data
            # Verify no requests were made
            assert len(mocked.requests) == 0

        # Clean up
        await client.close()

    @pytest.mark.asyncio
    async def test_get_weather_api_error(self, mock_weather_config, fast_weather_client):
        """Test handling of API errors."""
        
        client = fast_weather_client(mock_weather_config)
        
        with aioresponses() as mocked:
            # Mock API error response using URL pattern
            url_pattern = "https://api.openweathermap.org/data/2.5/weather"
            mocked.get(url_pattern, status=401, payload={"cod": 401, "message": "Invalid API key"})
            
            # With fast retry, we get tenacity.RetryError wrapping the original exception
            with pytest.raises((WeatherApiError, RetryError)):

                await client.get_weather(
                    latitude=mock_weather_config.default_latitude,
                    longitude=mock_weather_config.default_longitude,
                    units=mock_weather_config.units,
                )

        # Clean up
        await client.close()

    @pytest.mark.asyncio
    async def test_get_weather_request_exception(self, mock_weather_config, fast_weather_client):
        """Test handling of request exceptions."""

        client = fast_weather_client(mock_weather_config)
        
        with aioresponses() as mocked:
            # Mock connection error
            url = f"{client.API_BASE_URL}?lat={mock_weather_config.default_latitude}&lon={mock_weather_config.default_longitude}&units={mock_weather_config.units}&appid={mock_weather_config.api_key}"
            mocked.get(url, exception=aiohttp.ClientConnectionError("Connection failed"))
            
            with pytest.raises((WeatherApiError, RetryError)):
                await client.get_weather(
                    latitude=mock_weather_config.default_latitude,
                    longitude=mock_weather_config.default_longitude,
                    units=mock_weather_config.units,
                )

        # Clean up
        await client.close()

    @pytest.mark.asyncio
    async def test_get_weather_parsing_error(self, mock_weather_config):
        """Test handling of data parsing errors."""
        client = WeatherClient(mock_weather_config)

        with aioresponses() as mocked:
            # Return incomplete data
            url = f"{client.API_BASE_URL}?lat={mock_weather_config.default_latitude}&lon={mock_weather_config.default_longitude}&units={mock_weather_config.units}&appid={mock_weather_config.api_key}"
            mocked.get(url, status=200, payload={"cod": 200, "weather": []})

            with pytest.raises(
                WeatherClientError, match="Failed to parse weather data"
            ):
                await client.get_weather(
                    latitude=mock_weather_config.default_latitude,
                    longitude=mock_weather_config.default_longitude,
                    units=mock_weather_config.units,
                )

        # Clean up
        await client.close()

    @pytest.mark.asyncio
    async def test_get_weather_with_custom_coordinates(
        self, mock_weather_config, sample_weather_api_response
    ):
        """Test weather retrieval with custom coordinates."""
        client = WeatherClient(mock_weather_config)

        custom_lat = "40.7128"
        custom_lon = "-74.0060"

        with aioresponses() as mocked:
            # Mock the API response with custom coordinates
            url = f"{client.API_BASE_URL}?lat={custom_lat}&lon={custom_lon}&units={mock_weather_config.units}&appid={mock_weather_config.api_key}"
            mocked.get(url, status=200, payload=sample_weather_api_response)

            await client.get_weather(
                latitude=custom_lat,
                longitude=custom_lon,
                units=mock_weather_config.units,
            )

            # Verify request was made with custom coordinates
            assert len(mocked.requests) == 1
            request_url = str(list(mocked.requests.keys())[0][1])
            assert custom_lat in request_url
            assert custom_lon in request_url

        # Clean up
        await client.close()

    @pytest.mark.asyncio
    async def test_get_weather_with_imperial_units(self, mock_weather_config, sample_weather_api_response):
        """Test weather retrieval with imperial units."""
        client = WeatherClient(mock_weather_config)
        
        with aioresponses() as mocked:
            # Mock the API response with imperial units
            url = f"{client.API_BASE_URL}?lat={mock_weather_config.default_latitude}&lon={mock_weather_config.default_longitude}&units=imperial&appid={mock_weather_config.api_key}"
            mocked.get(url, status=200, payload=sample_weather_api_response)
            
            result = await client.get_weather(
                latitude=mock_weather_config.default_latitude,
                longitude=mock_weather_config.default_longitude,
                units="imperial"
            )
            
            assert isinstance(result, WeatherData)
            # Verify request was made with imperial units
            assert len(mocked.requests) == 1
            request_url = str(list(mocked.requests.keys())[0][1])
            assert "units=imperial" in request_url
        
        # Clean up
        await client.close()

    @pytest.mark.asyncio
    async def test_ensure_session_recreates_closed_session(self, mock_weather_config):
        """Test that _ensure_session recreates a closed session."""
        client = WeatherClient(mock_weather_config)
        
        # Create and close first session
        session1 = await client._ensure_session()
        await session1.close()
        
        # Get session again - should create new one
        session2 = await client._ensure_session()
        assert session2 is not session1
        assert not session2.closed
        
        # Clean up
        await client.close()

    @pytest.mark.asyncio
    async def test_get_weather_api_error_response(self, mock_weather_config, fast_weather_client):
        """Test handling of API error in response body."""
        client = fast_weather_client(mock_weather_config)
        
        with aioresponses() as mocked:
            # Mock API error in response body
            url = f"{client.API_BASE_URL}?lat={mock_weather_config.default_latitude}&lon={mock_weather_config.default_longitude}&units={mock_weather_config.units}&appid={mock_weather_config.api_key}"
            mocked.get(url, status=200, payload={"cod": 401, "message": "Invalid API key"})
            
            with pytest.raises((WeatherApiError, RetryError)):
                await client.get_weather(
                    latitude=mock_weather_config.default_latitude,
                    longitude=mock_weather_config.default_longitude,
                    units=mock_weather_config.units
                )
        
        # Clean up
        await client.close()

    @pytest.mark.asyncio
    async def test_get_weather_unexpected_exception(self, mock_weather_config):
        """Test handling of unexpected exceptions."""
        client = WeatherClient(mock_weather_config)
        
        # Mock an unexpected exception in from_api_response
        with patch.object(WeatherData, 'from_api_response', side_effect=ValueError("Unexpected error")):
            with aioresponses() as mocked:
                url = f"{client.API_BASE_URL}?lat={mock_weather_config.default_latitude}&lon={mock_weather_config.default_longitude}&units={mock_weather_config.units}&appid={mock_weather_config.api_key}"
                mocked.get(url, status=200, payload={"cod": 200, "weather": [{"description": "clear"}], "main": {"temp": 20, "humidity": 50}})
                
                with pytest.raises(WeatherClientError, match="Unexpected error getting weather data"):
                    await client.get_weather(
                        latitude=mock_weather_config.default_latitude,
                        longitude=mock_weather_config.default_longitude,
                        units=mock_weather_config.units
                    )
        
        # Clean up
        await client.close()

    @pytest.mark.asyncio
    async def test_cache_stores_and_retrieves_correctly(self, mock_weather_config, sample_weather_data):
        """Test that cache stores and retrieves data correctly with timing."""
        client = WeatherClient(mock_weather_config)
        
        cache_key = "test:cache:metric"
        
        # Store in cache
        client._store_in_cache(cache_key, sample_weather_data)
        
        # Verify storage
        assert cache_key in client._cache
        stored_time, stored_data = client._cache[cache_key]
        assert stored_data == sample_weather_data
        assert isinstance(stored_time, float)
        
        # Retrieve from cache
        retrieved_data = client._get_from_cache(cache_key)
        assert retrieved_data == sample_weather_data

    def test_cache_key_with_different_parameters(self, mock_weather_config):
        """Test cache key generation with various parameter combinations."""
        client = WeatherClient(mock_weather_config)
        
        # Test different combinations
        key1 = client._get_cache_key("0", "0", "metric")
        key2 = client._get_cache_key("0", "0", "imperial")
        key3 = client._get_cache_key("1", "0", "metric")
        key4 = client._get_cache_key("0", "1", "metric")
        
        # All keys should be different
        keys = [key1, key2, key3, key4]
        assert len(set(keys)) == 4
        
        # Check format
        assert key1 == "0:0:metric"
        assert key2 == "0:0:imperial"
        assert key3 == "1:0:metric"
        assert key4 == "0:1:metric"


class TestGetWeatherClient:
    """Test cases for get_weather_client function."""

    @patch("mcp_server_weather.weather.module.get_weather_config")
    @patch("mcp_server_weather.weather.module.WeatherClient")
    def test_get_weather_client_caching(self, mock_client_class, mock_get_config):
        """Test that get_weather_client caches instances."""
        # Clear the cache to ensure clean test state
        get_weather_client.cache_clear()
        
        # Setup mocks
        mock_config = Mock()
        mock_get_config.return_value = mock_config
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # First call should create a new instance
        client1 = get_weather_client()
        assert client1 == mock_client
        mock_get_config.assert_called_once()
        mock_client_class.assert_called_once_with(mock_config)

        # Reset mocks
        mock_get_config.reset_mock()
        mock_client_class.reset_mock()

        # Second call should return cached instance
        client2 = get_weather_client()
        assert client2 == mock_client
        mock_get_config.assert_not_called()
        mock_client_class.assert_not_called()

        # Verify same instance
        assert client1 is client2
        
    def test_get_weather_client_clear_cache(self):
        """Test clearing the LRU cache."""
        # Clear the cache to ensure clean test state
        get_weather_client.cache_clear()
        
        with patch('mcp_server_weather.weather.module.get_weather_config') as mock_get_config, \
             patch('mcp_server_weather.weather.module.WeatherClient') as mock_client_class:
            
            mock_config = Mock()
            mock_get_config.return_value = mock_config
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            
            # Should create new instance after cache clear
            client = get_weather_client()
            assert client == mock_client
            mock_get_config.assert_called_once()
            mock_client_class.assert_called_once_with(mock_config)

    @patch('mcp_server_weather.weather.module.get_weather_config')
    def test_get_weather_client_config_error(self, mock_get_config):
        """Test handling of configuration errors in get_weather_client."""
        # Clear the cache first
        get_weather_client.cache_clear()
        
        mock_get_config.side_effect = WeatherConfigError("Configuration error")
        
        with pytest.raises(WeatherConfigError, match="Configuration error"):
            get_weather_client() 


class TestRetryLogic:
    """Test cases for retry decorator and logic."""
    
    @pytest.mark.asyncio
    async def test_retry_on_client_error(self, mock_weather_config, fast_weather_client):
        """Test that retry works on aiohttp ClientError."""
        client = fast_weather_client(mock_weather_config)
        
        with aioresponses() as mocked:
            url = f"{client.API_BASE_URL}?lat={mock_weather_config.default_latitude}&lon={mock_weather_config.default_longitude}&units={mock_weather_config.units}&appid={mock_weather_config.api_key}"
            
            # First few calls fail, last one succeeds
            mocked.get(url, exception=aiohttp.ClientConnectionError("Connection failed"))
            mocked.get(url, exception=aiohttp.ClientConnectionError("Connection failed"))
            mocked.get(url, status=200, payload={
                "cod": 200,
                "weather": [{"description": "clear sky"}],
                "main": {"temp": 20, "humidity": 50}
            })
            
            # Should eventually succeed after retries
            result = await client.get_weather(
                latitude=mock_weather_config.default_latitude,
                longitude=mock_weather_config.default_longitude,
                units=mock_weather_config.units
            )
            
            assert isinstance(result, WeatherData)
            # With aioresponses, we get a single key but multiple calls
            url_key = list(mocked.requests.keys())[0]
            assert len(mocked.requests[url_key]) == 3
        
        await client.close()

    @pytest.mark.asyncio
    async def test_retry_on_weather_api_error(self, mock_weather_config, fast_weather_client):
        """Test that retry works on WeatherApiError."""
        client = fast_weather_client(mock_weather_config)
        
        with aioresponses() as mocked:
            url = f"{client.API_BASE_URL}?lat={mock_weather_config.default_latitude}&lon={mock_weather_config.default_longitude}&units={mock_weather_config.units}&appid={mock_weather_config.api_key}"
            
            # First call fails with API error, second succeeds
            mocked.get(url, status=503, payload={"message": "Service unavailable"})
            mocked.get(url, status=200, payload={
                "cod": 200,
                "weather": [{"description": "clear sky"}],
                "main": {"temp": 20, "humidity": 50}
            })
            
            result = await client.get_weather(
                latitude=mock_weather_config.default_latitude,
                longitude=mock_weather_config.default_longitude,
                units=mock_weather_config.units
            )
            
            assert isinstance(result, WeatherData)
            url_key = list(mocked.requests.keys())[0]
            assert len(mocked.requests[url_key]) == 2
        
        await client.close()

    @pytest.mark.asyncio
    async def test_retry_exhausted(self, mock_weather_config, fast_weather_client):
        """Test behavior when all retry attempts are exhausted."""
        client = fast_weather_client(mock_weather_config)
        
        with aioresponses() as mocked:
            url = f"{client.API_BASE_URL}?lat={mock_weather_config.default_latitude}&lon={mock_weather_config.default_longitude}&units={mock_weather_config.units}&appid={mock_weather_config.api_key}"
            
            # All calls fail
            for _ in range(10):  # More than max retries
                mocked.get(url, exception=aiohttp.ClientConnectionError("Connection failed"))
            
            with pytest.raises((WeatherApiError, RetryError)):
                await client.get_weather(
                    latitude=mock_weather_config.default_latitude,
                    longitude=mock_weather_config.default_longitude,
                    units=mock_weather_config.units
                )
            
            # Should have made 3 attempts (stop_after_attempt(3) in fast retry)
            url_key = list(mocked.requests.keys())[0]
            assert len(mocked.requests[url_key]) == 3
        
        await client.close()


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    @pytest.mark.asyncio
    async def test_get_weather_empty_coordinates(self, mock_weather_config, fast_weather_client):
        """Test handling of empty coordinates."""
        client = fast_weather_client(mock_weather_config)
        
        with aioresponses() as mocked:
            url = f"{client.API_BASE_URL}?lat=&lon=&units={mock_weather_config.units}&appid={mock_weather_config.api_key}"
            mocked.get(url, status=400, payload={"cod": "400", "message": "wrong latitude"})
            
            with pytest.raises((WeatherApiError, RetryError)):
                await client.get_weather(latitude="", longitude="", units=mock_weather_config.units)
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_get_weather_invalid_json_response(self, mock_weather_config, fast_weather_client):
        """Test handling of invalid JSON response."""
        client = fast_weather_client(mock_weather_config)
        
        with aioresponses() as mocked:
            url = f"{client.API_BASE_URL}?lat={mock_weather_config.default_latitude}&lon={mock_weather_config.default_longitude}&units={mock_weather_config.units}&appid={mock_weather_config.api_key}"
            mocked.get(url, status=200, body="invalid json")
            
            with pytest.raises((WeatherApiError, WeatherClientError)):
                await client.get_weather(
                    latitude=mock_weather_config.default_latitude,
                    longitude=mock_weather_config.default_longitude,
                    units=mock_weather_config.units
                )
        
        await client.close()

    def test_cache_with_zero_ttl(self, mock_weather_config, sample_weather_data):
        """Test cache behavior with zero TTL."""
        mock_weather_config.cache_ttl_seconds = 0
        client = WeatherClient(mock_weather_config)
        
        cache_key = "test-key"
        client._store_in_cache(cache_key, sample_weather_data)
        
        # Should immediately expire
        result = client._get_from_cache(cache_key)
        assert result is None
        assert cache_key not in client._cache

    def test_multiple_cache_entries(self, mock_weather_config, sample_weather_data):
        """Test cache with multiple entries."""
        client = WeatherClient(mock_weather_config)
        
        # Add multiple entries
        for i in range(5):
            cache_key = f"test-key-{i}"
            client._store_in_cache(cache_key, sample_weather_data)
        
        assert len(client._cache) == 5
        
        # All should be retrievable
        for i in range(5):
            cache_key = f"test-key-{i}"
            result = client._get_from_cache(cache_key)
            assert result == sample_weather_data

    @pytest.mark.asyncio 
    async def test_session_timeout_configuration(self, mock_weather_config):
        """Test that session is configured with correct timeout."""
        mock_weather_config.timeout_seconds = 10
        client = WeatherClient(mock_weather_config)
        
        session = await client._ensure_session()
        assert session.timeout.total == 10
        
        await client.close()

    def test_api_base_url_constant(self):
        """Test that API base URL is correctly defined."""
        assert WeatherClient.API_BASE_URL == "https://api.openweathermap.org/data/2.5/weather"


class TestLoggingAndObservability:
    """Test logging and observability features."""
    
    def test_weather_client_initialization_logging(self, mock_weather_config, caplog):
        """Test that WeatherClient initialization is logged."""
        with caplog.at_level('INFO'):
            client = WeatherClient(mock_weather_config)
            
        assert "WeatherClient initialized" in caplog.text
    
    @pytest.mark.asyncio
    async def test_cache_hit_logging(self, mock_weather_config, sample_weather_data, caplog):
        """Test that cache hits are logged."""
        client = WeatherClient(mock_weather_config)
        
        # Add item to cache
        cache_key = "test-cache-key"
        client._store_in_cache(cache_key, sample_weather_data)
        
        with caplog.at_level('DEBUG'):
            client._get_from_cache(cache_key)
        
        assert f"Cache hit for {cache_key}" in caplog.text
    
    @pytest.mark.asyncio
    async def test_cache_store_logging(self, mock_weather_config, sample_weather_data, caplog):
        """Test that cache storage is logged."""
        client = WeatherClient(mock_weather_config)
        
        cache_key = "test-store-key"
        
        with caplog.at_level('DEBUG'):
            client._store_in_cache(cache_key, sample_weather_data)
        
        assert f"Stored in cache: {cache_key}" in caplog.text
    
    @pytest.mark.asyncio
    async def test_weather_request_logging(self, mock_weather_config, sample_weather_api_response, caplog):
        """Test that weather requests are logged."""
        client = WeatherClient(mock_weather_config)
        
        with aioresponses() as mocked:
            url = f"{client.API_BASE_URL}?lat={mock_weather_config.default_latitude}&lon={mock_weather_config.default_longitude}&units={mock_weather_config.units}&appid={mock_weather_config.api_key}"
            mocked.get(url, status=200, payload=sample_weather_api_response)
            
            with caplog.at_level('INFO'):
                await client.get_weather(
                    latitude=mock_weather_config.default_latitude,
                    longitude=mock_weather_config.default_longitude,
                    units=mock_weather_config.units
                )
            
            assert f"Fetching weather data for coordinates: {mock_weather_config.default_latitude}, {mock_weather_config.default_longitude}" in caplog.text
            assert "Successfully retrieved weather data:" in caplog.text
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_error_logging(self, mock_weather_config, caplog, fast_weather_client):
        """Test that errors are properly logged."""
        client = fast_weather_client(mock_weather_config)
        
        with aioresponses() as mocked:
            # Use base URL without parameters
            mocked.get(client.API_BASE_URL, status=404, body="Not Found")
            
            with caplog.at_level('ERROR'):
                try:
                    await client.get_weather(
                        latitude=mock_weather_config.default_latitude,
                        longitude=mock_weather_config.default_longitude,
                        units=mock_weather_config.units
                    )
                except (WeatherApiError, RetryError):
                    pass
            
            assert "Request error:" in caplog.text
        
        await client.close()


class TestIntegrationScenarios:
    """Integration test scenarios combining multiple features."""
    
    @pytest.mark.asyncio
    async def test_cache_integration_full_cycle(self, mock_weather_config, sample_weather_api_response):
        """Test full cache integration cycle."""
        client = WeatherClient(mock_weather_config)
        
        lat, lon, units = "51.5074", "-0.1278", "metric"
        
        with aioresponses() as mocked:
            url = f"{client.API_BASE_URL}?lat={lat}&lon={lon}&units={units}&appid={mock_weather_config.api_key}"
            mocked.get(url, status=200, payload=sample_weather_api_response)
            
            # First request - should hit API and cache result
            result1 = await client.get_weather(latitude=lat, longitude=lon, units=units)
            assert len(mocked.requests) == 1
            
            # Second request - should get from cache
            result2 = await client.get_weather(latitude=lat, longitude=lon, units=units)
            assert len(mocked.requests) == 1  # No additional requests
            assert result1 == result2
            
            # Verify cache contains the data
            cache_key = client._get_cache_key(lat, lon, units)
            assert cache_key in client._cache
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_different_units_different_cache(self, mock_weather_config, sample_weather_api_response):
        """Test that different units result in different cache entries."""
        client = WeatherClient(mock_weather_config)
        
        lat, lon = "51.5074", "-0.1278"
        
        with aioresponses() as mocked:
            # Mock responses for different units
            url_metric = f"{client.API_BASE_URL}?lat={lat}&lon={lon}&units=metric&appid={mock_weather_config.api_key}"
            url_imperial = f"{client.API_BASE_URL}?lat={lat}&lon={lon}&units=imperial&appid={mock_weather_config.api_key}"
            
            mocked.get(url_metric, status=200, payload=sample_weather_api_response)
            mocked.get(url_imperial, status=200, payload=sample_weather_api_response)
            
            # Request with metric units
            await client.get_weather(latitude=lat, longitude=lon, units="metric")
            
            # Request with imperial units
            await client.get_weather(latitude=lat, longitude=lon, units="imperial")
            
            # Should have made 2 API calls (different cache entries)
            assert len(mocked.requests) == 2
            
            # Verify cache has 2 different entries
            cache_key_metric = client._get_cache_key(lat, lon, "metric")
            cache_key_imperial = client._get_cache_key(lat, lon, "imperial")
            
            assert cache_key_metric in client._cache
            assert cache_key_imperial in client._cache
            assert cache_key_metric != cache_key_imperial
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_error_handling_with_cache_disabled(self, mock_weather_config, fast_weather_client):
        """Test error handling when cache is disabled."""
        mock_weather_config.enable_caching = False
        client = fast_weather_client(mock_weather_config)
        
        with aioresponses() as mocked:
            url = f"{client.API_BASE_URL}?lat={mock_weather_config.default_latitude}&lon={mock_weather_config.default_longitude}&units={mock_weather_config.units}&appid={mock_weather_config.api_key}"
            mocked.get(url, status=500, payload={"message": "Internal server error"})
            
            with pytest.raises((WeatherApiError, RetryError)):
                await client.get_weather(
                    latitude=mock_weather_config.default_latitude,
                    longitude=mock_weather_config.default_longitude,
                    units=mock_weather_config.units
                )
            
            # Verify cache is empty
            assert len(client._cache) == 0
        
        await client.close()

    @pytest.mark.asyncio
    async def test_session_reuse_across_requests(self, mock_weather_config, sample_weather_api_response):
        """Test that HTTP session is reused across multiple requests."""
        client = WeatherClient(mock_weather_config)
        
        with aioresponses() as mocked:
            # Mock multiple requests
            for i in range(3):
                lat, lon = f"5{i}.5074", "-0.1278"
                url = f"{client.API_BASE_URL}?lat={lat}&lon={lon}&units={mock_weather_config.units}&appid={mock_weather_config.api_key}"
                mocked.get(url, status=200, payload=sample_weather_api_response)
            
            # Make multiple requests
            sessions = []
            for i in range(3):
                lat, lon = f"5{i}.5074", "-0.1278"
                await client.get_weather(latitude=lat, longitude=lon, units=mock_weather_config.units)
                sessions.append(client._session)
            
            # All should use the same session
            assert all(session is sessions[0] for session in sessions)
            assert not sessions[0].closed
        
        await client.close()
