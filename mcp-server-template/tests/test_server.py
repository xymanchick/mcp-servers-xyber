"""Test cases for MCP server and tools."""
import json
import pytest
from unittest.mock import Mock, patch, AsyncMock

from fastmcp import Context
from fastmcp.exceptions import ToolError

from mcp_server_weather.server import _get_weather_impl, app_lifespan
from mcp_server_weather.weather import WeatherApiError, WeatherClientError, WeatherData


class TestGetWeatherTool:
    """Test cases for get_weather tool."""
    
    @pytest.fixture
    def mock_context(self):
        """Create a mock MCP context."""
        context = Mock(spec=Context)
        context.request_context = Mock()
        context.request_context.lifespan_context = {
            "weather_client": Mock()
        }
        return context
    
    @pytest.mark.asyncio
    async def test_get_weather_success(self, mock_context):
        """Test successful weather retrieval."""
        # Setup mock weather client
        weather_client = mock_context.request_context.lifespan_context["weather_client"]
        weather_client.get_weather = AsyncMock(return_value=WeatherData(
            state="sunny",
            temperature="25.5C",
            humidity="60%"
        ))

        # Call the tool
        result = await _get_weather_impl(mock_context, "51.5074", "-0.1278")
        
        # Verify result
        assert result == {
            "state": "sunny",
            "temperature": "25.5C",
            "humidity": "60%"
        }
        
        # Verify weather client was called correctly
        weather_client.get_weather.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_weather_with_coordinates(self, mock_context):
        """Test weather retrieval with custom coordinates."""
        # Setup mock weather client
        weather_client = mock_context.request_context.lifespan_context["weather_client"]
        weather_client.get_weather = AsyncMock(return_value=WeatherData(
            state="cloudy",
            temperature="18.3C",
            humidity="75%"
        ))

        # Call the tool with coordinates
        result = await _get_weather_impl(
            mock_context,
            latitude="40.7128",
            longitude="-74.0060"
        )

        # Verify result
        assert result == {
            "state": "cloudy", 
            "temperature": "18.3C",
            "humidity": "75%"
        }

        # Verify weather client was called correctly
        weather_client.get_weather.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_weather_api_error(self, mock_context):
        """Test handling of API errors."""
        # Setup mock weather client to raise API error
        weather_client = mock_context.request_context.lifespan_context["weather_client"]
        weather_client.get_weather = AsyncMock(side_effect=WeatherApiError("API key invalid"))

        # Call the tool and expect error
        with pytest.raises(ToolError, match="Weather API error: API key invalid"):
            await _get_weather_impl(mock_context, "51.5074", "-0.1278")
    
    @pytest.mark.asyncio
    async def test_get_weather_client_error(self, mock_context):
        """Test handling of client errors."""
        # Setup mock weather client to raise client error
        weather_client = mock_context.request_context.lifespan_context["weather_client"]
        weather_client.get_weather = AsyncMock(side_effect=WeatherClientError("Failed to parse data"))

        # Call the tool and expect error
        with pytest.raises(ToolError, match="Weather client error: Failed to parse data"):
            await _get_weather_impl(mock_context, "51.5074", "-0.1278")
    
    @pytest.mark.asyncio
    async def test_get_weather_unexpected_error(self, mock_context):
        """Test handling of unexpected errors."""
        # Setup mock weather client to raise unexpected error
        weather_client = mock_context.request_context.lifespan_context["weather_client"]
        weather_client.get_weather = AsyncMock(side_effect=ValueError("Unexpected error"))

        # Call the tool and expect error
        with pytest.raises(ToolError, match="An unexpected error occurred processing weather request"):
            await _get_weather_impl(mock_context, "51.5074", "-0.1278")


class TestAppLifespan:
    """Test cases for app_lifespan context manager."""
    
    @pytest.mark.asyncio
    async def test_app_lifespan_success(self):
        """Test successful lifespan initialization."""
        # Mock server
        server = Mock()
        
        # Mock get_weather_client
        with patch('mcp_server_weather.server.get_weather_client') as mock_get_client:
            mock_client = Mock()
            mock_get_client.return_value = mock_client
            
            # Use lifespan context manager
            async with app_lifespan(server) as context:
                # Verify context has weather client
                assert "weather_client" in context
                assert context["weather_client"] == mock_client
                
                # Verify client was initialized
                mock_get_client.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_app_lifespan_weather_error(self):
        """Test lifespan with weather initialization error."""
        # Mock server
        server = Mock()
        
        # Mock get_weather_client to raise error
        with patch('mcp_server_weather.server.get_weather_client') as mock_get_client:
            mock_get_client.side_effect = WeatherApiError("Failed to initialize")
            
            # Use lifespan context manager and expect error
            with pytest.raises(WeatherApiError, match="Failed to initialize"):
                async with app_lifespan(server) as context:
                    pass  # Should not reach here
    
    @pytest.mark.asyncio
    async def test_app_lifespan_unexpected_error(self):
        """Test lifespan with unexpected initialization error."""
        # Mock server
        server = Mock()
        
        # Mock get_weather_client to raise unexpected error
        with patch('mcp_server_weather.server.get_weather_client') as mock_get_client:
            mock_get_client.side_effect = Exception("Unexpected initialization error")
            
            # Use lifespan context manager and expect error
            with pytest.raises(Exception, match="Unexpected initialization error"):
                async with app_lifespan(server) as context:
                    pass  # Should not reach here 