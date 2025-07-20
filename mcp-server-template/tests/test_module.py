"""Test cases for WeatherClient module."""
import json
import pytest
import time
from unittest.mock import Mock, patch, MagicMock

import aiohttp
from aioresponses import aioresponses

from mcp_server_weather.weather.module import WeatherClient, get_weather_client
from mcp_server_weather.weather.config import (
    WeatherApiError,
    WeatherClientError,
    WeatherConfigError,
    get_weather_config,
)
from mcp_server_weather.weather.models import WeatherData


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
            units=mock_weather_config.units
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
        params = client._build_request_params(latitude="40.7128", longitude="-74.0060", units="imperial")
        
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
        client._cache[cache_key] = (time.time() - 600, sample_weather_data)  # 10 minutes old
        
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
    async def test_get_weather_success(self, mock_weather_config, sample_weather_api_response):
        """Test successful weather retrieval."""
        client = WeatherClient(mock_weather_config)
        
        with aioresponses() as mocked:
            # Mock the API response
            url = f"{client.API_BASE_URL}?lat={mock_weather_config.default_latitude}&lon={mock_weather_config.default_longitude}&units={mock_weather_config.units}&appid={mock_weather_config.api_key}"
            mocked.get(url, status=200, payload=sample_weather_api_response)
            
            result = await client.get_weather(
                latitude=mock_weather_config.default_latitude,
                longitude=mock_weather_config.default_longitude,
                units=mock_weather_config.units
            )
            
            assert isinstance(result, WeatherData)
            assert result.state == "clear sky"
            assert result.temperature == "15.5C"
            assert result.humidity == "76%"
            
        # Clean up
        await client.close()
    
    @pytest.mark.asyncio
    async def test_get_weather_from_cache(self, mock_weather_config, sample_weather_data):
        """Test retrieving weather from cache."""
        client = WeatherClient(mock_weather_config)
        
        # Add item to cache
        cache_key = client._get_cache_key(
            mock_weather_config.default_latitude, 
            mock_weather_config.default_longitude,
            mock_weather_config.units
        )
        client._cache[cache_key] = (time.time(), sample_weather_data)
        
        with aioresponses() as mocked:
            # API should not be called
            result = await client.get_weather(
                latitude=mock_weather_config.default_latitude,
                longitude=mock_weather_config.default_longitude,
                units=mock_weather_config.units
            )
            
            assert result == sample_weather_data
            # Verify no requests were made
            assert len(mocked.requests) == 0
        
        # Clean up
        await client.close()
    
    @pytest.mark.asyncio
    async def test_get_weather_api_error(self, mock_weather_config):
        """Test handling of API errors."""
        client = WeatherClient(mock_weather_config)
        
        with aioresponses() as mocked:
            # Mock API error response
            url = f"{client.API_BASE_URL}?lat={mock_weather_config.default_latitude}&lon={mock_weather_config.default_longitude}&units={mock_weather_config.units}&appid={mock_weather_config.api_key}"
            mocked.get(url, status=401, payload={"cod": 401, "message": "Invalid API key"})
            
            with pytest.raises(WeatherApiError, match="Failed to connect to OpenWeatherMap API|OpenWeatherMap API HTTP error: 401"):
                await client.get_weather(
                    latitude=mock_weather_config.default_latitude,
                    longitude=mock_weather_config.default_longitude,
                    units=mock_weather_config.units
                )
        
        # Clean up
        await client.close()
    
    @pytest.mark.asyncio
    async def test_get_weather_request_exception(self, mock_weather_config):
        """Test handling of request exceptions."""
        client = WeatherClient(mock_weather_config)
        
        with aioresponses() as mocked:
            # Mock connection error
            url = f"{client.API_BASE_URL}?lat={mock_weather_config.default_latitude}&lon={mock_weather_config.default_longitude}&units={mock_weather_config.units}&appid={mock_weather_config.api_key}"
            mocked.get(url, exception=aiohttp.ClientConnectionError("Connection failed"))
            
            with pytest.raises(WeatherApiError, match="Failed to connect to OpenWeatherMap API"):
                await client.get_weather(
                    latitude=mock_weather_config.default_latitude,
                    longitude=mock_weather_config.default_longitude,
                    units=mock_weather_config.units
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
            
            with pytest.raises(WeatherClientError, match="Failed to parse weather data"):
                await client.get_weather(
                    latitude=mock_weather_config.default_latitude,
                    longitude=mock_weather_config.default_longitude,
                    units=mock_weather_config.units
                )
        
        # Clean up
        await client.close()
    
    @pytest.mark.asyncio
    async def test_get_weather_with_custom_coordinates(self, mock_weather_config, sample_weather_api_response):
        """Test weather retrieval with custom coordinates."""
        client = WeatherClient(mock_weather_config)
        
        custom_lat = "40.7128"
        custom_lon = "-74.0060"
        
        with aioresponses() as mocked:
            # Mock the API response with custom coordinates
            url = f"{client.API_BASE_URL}?lat={custom_lat}&lon={custom_lon}&units={mock_weather_config.units}&appid={mock_weather_config.api_key}"
            mocked.get(url, status=200, payload=sample_weather_api_response)
            
            await client.get_weather(latitude=custom_lat, longitude=custom_lon, units=mock_weather_config.units)
            
            # Verify request was made with custom coordinates
            assert len(mocked.requests) == 1
            request_url = str(list(mocked.requests.keys())[0][1])
            assert custom_lat in request_url
            assert custom_lon in request_url
        
        # Clean up
        await client.close()


class TestGetWeatherClient:
    """Test cases for get_weather_client function."""
    
    @patch('mcp_server_weather.weather.module.get_weather_config')
    @patch('mcp_server_weather.weather.module.WeatherClient')
    def test_get_weather_client_caching(self, mock_client_class, mock_get_config):
        """Test that get_weather_client caches instances."""
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