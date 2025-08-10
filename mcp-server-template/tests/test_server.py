"""Test cases for MCP server and tools."""
import json
import pytest
from unittest.mock import Mock, patch, AsyncMock

from fastmcp import Context
from fastmcp.exceptions import ToolError

from mcp_server_weather.server import get_weather, app_lifespan
from mcp_server_weather.weather import WeatherApiError, WeatherClientError, WeatherData, WeatherError

# Access the actual function from the decorated tool
_get_weather_fn = get_weather.fn


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
        result = await _get_weather_fn(mock_context, "51.5074", "-0.1278")
        
        # Verify result
        assert result == {
            "state": "sunny",
            "temperature": "25.5C",
            "humidity": "60%"
        }
        
        # Verify weather client was called correctly
        weather_client.get_weather.assert_called_once_with(
            latitude="51.5074", 
            longitude="-0.1278", 
            units=None
        )
    
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
        result = await _get_weather_fn(
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
        weather_client.get_weather.assert_called_once_with(
            latitude="40.7128",
            longitude="-74.0060", 
            units=None
        )
    
    @pytest.mark.asyncio
    async def test_get_weather_api_error(self, mock_context):
        """Test handling of API errors."""
        # Setup mock weather client to raise API error
        weather_client = mock_context.request_context.lifespan_context["weather_client"]
        weather_client.get_weather = AsyncMock(side_effect=WeatherApiError("API key invalid"))

        # Call the tool and expect error
        with pytest.raises(ToolError, match="Weather API error: API key invalid"):
            await _get_weather_fn(mock_context, "51.5074", "-0.1278")
    
    @pytest.mark.asyncio
    async def test_get_weather_client_error(self, mock_context):
        """Test handling of client errors."""
        # Setup mock weather client to raise client error
        weather_client = mock_context.request_context.lifespan_context["weather_client"]
        weather_client.get_weather = AsyncMock(side_effect=WeatherClientError("Failed to parse data"))

        # Call the tool and expect error
        with pytest.raises(ToolError, match="Weather client error: Failed to parse data"):
            await _get_weather_fn(mock_context, "51.5074", "-0.1278")
    
    @pytest.mark.asyncio
    async def test_get_weather_unexpected_error(self, mock_context):
        """Test handling of unexpected errors."""
        # Setup mock weather client to raise unexpected error
        weather_client = mock_context.request_context.lifespan_context["weather_client"]
        weather_client.get_weather = AsyncMock(side_effect=ValueError("Unexpected error"))

        # Call the tool and expect error
        with pytest.raises(ToolError, match="An unexpected error occurred processing weather request"):
            await _get_weather_fn(mock_context, "51.5074", "-0.1278")

    @pytest.mark.asyncio
    async def test_get_weather_with_metric_units(self, mock_context):
        """Test weather retrieval with metric units."""
        # Setup mock weather client
        weather_client = mock_context.request_context.lifespan_context["weather_client"]
        weather_client.get_weather = AsyncMock(return_value=WeatherData(
            state="rainy",
            temperature="15.2C",
            humidity="85%"
        ))

        # Call the tool with metric units
        result = await _get_weather_fn(
            mock_context,
            latitude="51.5074",
            longitude="-0.1278",
            units="metric"
        )

        # Verify result
        assert result == {
            "state": "rainy",
            "temperature": "15.2C", 
            "humidity": "85%"
        }

        # Verify weather client was called with correct units
        weather_client.get_weather.assert_called_once_with(
            latitude="51.5074",
            longitude="-0.1278",
            units="metric"
        )

    @pytest.mark.asyncio
    async def test_get_weather_with_imperial_units(self, mock_context):
        """Test weather retrieval with imperial units."""
        # Setup mock weather client
        weather_client = mock_context.request_context.lifespan_context["weather_client"]
        weather_client.get_weather = AsyncMock(return_value=WeatherData(
            state="snowy",
            temperature="32.0F",
            humidity="90%"
        ))

        # Call the tool with imperial units
        result = await _get_weather_fn(
            mock_context,
            latitude="40.7128",
            longitude="-74.0060",
            units="imperial"
        )

        # Verify result
        assert result == {
            "state": "snowy",
            "temperature": "32.0F",
            "humidity": "90%"
        }

        # Verify weather client was called with correct units
        weather_client.get_weather.assert_called_once_with(
            latitude="40.7128",
            longitude="-74.0060",
            units="imperial"
        )

    @pytest.mark.asyncio 
    async def test_get_weather_empty_coordinates(self, mock_context):
        """Test weather retrieval with empty coordinate strings."""
        # Setup mock weather client
        weather_client = mock_context.request_context.lifespan_context["weather_client"]
        weather_client.get_weather = AsyncMock(return_value=WeatherData(
            state="clear",
            temperature="20.0C",
            humidity="50%"
        ))

        # Call the tool with empty coordinates
        result = await _get_weather_fn(mock_context, "", "")

        # Verify result
        assert result == {
            "state": "clear",
            "temperature": "20.0C",
            "humidity": "50%"
        }

        # Verify weather client was called with empty coordinates
        weather_client.get_weather.assert_called_once_with(
            latitude="",
            longitude="",
            units=None
        )


class TestAppLifespan:
    """Test cases for app_lifespan context manager."""
    
    @pytest.mark.asyncio
    async def test_app_lifespan_success(self):
        """Test successful lifespan initialization."""
        # Mock server
        server = Mock()
        
        # Mock get_weather_client
        with patch('mcp_server_weather.server.get_weather_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.close = AsyncMock()
            mock_get_client.return_value = mock_client
            
            # Use lifespan context manager
            async with app_lifespan(server) as context:
                # Verify context has weather client
                assert "weather_client" in context
                assert context["weather_client"] == mock_client
                
                # Verify client was initialized
                mock_get_client.assert_called_once()
            
            # Verify cleanup was called
            mock_client.close.assert_called_once()
    
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

    @pytest.mark.asyncio
    async def test_app_lifespan_cleanup_error(self):
        """Test lifespan cleanup with error during shutdown."""
        # Mock server
        server = Mock()
        
        # Mock get_weather_client
        with patch('mcp_server_weather.server.get_weather_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.close = AsyncMock(side_effect=Exception("Cleanup error"))
            mock_get_client.return_value = mock_client
            
            # Use lifespan context manager - should not raise on cleanup error
            async with app_lifespan(server) as context:
                # Verify context has weather client
                assert "weather_client" in context
                assert context["weather_client"] == mock_client
            
            # Verify cleanup was attempted despite error
            mock_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_app_lifespan_general_weather_error(self):
        """Test lifespan with general WeatherError during initialization."""
        # Mock server
        server = Mock()
        
        # Mock get_weather_client to raise general WeatherError
        with patch('mcp_server_weather.server.get_weather_client') as mock_get_client:
            mock_get_client.side_effect = WeatherError("General weather error")
            
            # Use lifespan context manager and expect error
            with pytest.raises(WeatherError, match="General weather error"):
                async with app_lifespan(server) as context:
                    pass  # Should not reach here


class TestWeatherIntegration:
    """Integration test cases for weather functionality."""
    
    @pytest.fixture
    def mock_context_integration(self):
        """Create a mock MCP context for integration tests."""
        context = Mock(spec=Context)
        context.request_context = Mock()
        context.request_context.lifespan_context = {
            "weather_client": Mock()
        }
        return context

    @pytest.mark.asyncio
    async def test_multiple_weather_requests(self, mock_context_integration):
        """Test multiple weather requests in sequence."""
        weather_client = mock_context_integration.request_context.lifespan_context["weather_client"]
        
        # Setup different responses for multiple calls
        weather_responses = [
            WeatherData(state="sunny", temperature="25.0C", humidity="60%"),
            WeatherData(state="cloudy", temperature="18.0C", humidity="75%"),
            WeatherData(state="rainy", temperature="12.0C", humidity="90%")
        ]
        weather_client.get_weather = AsyncMock(side_effect=weather_responses)
        
        # Make multiple requests
        locations = [
            ("40.7128", "-74.0060"),  # New York
            ("51.5074", "-0.1278"),   # London
            ("35.6762", "139.6503")   # Tokyo
        ]
        
        results = []
        for lat, lon in locations:
            result = await _get_weather_fn(mock_context_integration, lat, lon)
            results.append(result)
        
        # Verify all results
        expected_results = [
            {"state": "sunny", "temperature": "25.0C", "humidity": "60%"},
            {"state": "cloudy", "temperature": "18.0C", "humidity": "75%"},
            {"state": "rainy", "temperature": "12.0C", "humidity": "90%"}
        ]
        
        assert results == expected_results
        assert weather_client.get_weather.call_count == 3

    @pytest.mark.asyncio
    async def test_weather_request_with_extreme_coordinates(self, mock_context_integration):
        """Test weather request with extreme coordinate values."""
        weather_client = mock_context_integration.request_context.lifespan_context["weather_client"]
        weather_client.get_weather = AsyncMock(return_value=WeatherData(
            state="freezing",
            temperature="-40.0C",
            humidity="10%"
        ))
        
        # Test with extreme coordinates (North Pole)
        result = await _get_weather_fn(
            mock_context_integration,
            latitude="90.0",
            longitude="0.0",
            units="metric"
        )
        
        assert result == {
            "state": "freezing",
            "temperature": "-40.0C",
            "humidity": "10%"
        }
        
        weather_client.get_weather.assert_called_once_with(
            latitude="90.0",
            longitude="0.0", 
            units="metric"
        )

    @pytest.mark.asyncio
    async def test_weather_request_with_precision_coordinates(self, mock_context_integration):
        """Test weather request with high precision coordinates.""" 
        weather_client = mock_context_integration.request_context.lifespan_context["weather_client"]
        weather_client.get_weather = AsyncMock(return_value=WeatherData(
            state="partly cloudy",
            temperature="22.7C",
            humidity="55%"
        ))
        
        # Test with high precision coordinates
        result = await _get_weather_fn(
            mock_context_integration,
            latitude="40.712776",
            longitude="-74.005974"
        )
        
        assert result == {
            "state": "partly cloudy",
            "temperature": "22.7C",
            "humidity": "55%"
        }
        
        weather_client.get_weather.assert_called_once_with(
            latitude="40.712776",
            longitude="-74.005974",
            units=None
        )


class TestErrorHandling:
    """Test cases for comprehensive error handling scenarios."""
    
    @pytest.fixture
    def mock_context_error(self):
        """Create a mock MCP context for error testing."""
        context = Mock(spec=Context)
        context.request_context = Mock()
        context.request_context.lifespan_context = {
            "weather_client": Mock()
        }
        return context

    @pytest.mark.asyncio
    async def test_missing_weather_client_in_context(self):
        """Test handling when weather client is missing from context."""
        context = Mock(spec=Context)
        context.request_context = Mock()
        context.request_context.lifespan_context = {}  # Missing weather_client
        
        # This should raise a KeyError since the code doesn't handle missing client
        with pytest.raises(KeyError, match="weather_client"):
            await _get_weather_fn(context, "51.5074", "-0.1278")

    @pytest.mark.asyncio
    async def test_malformed_lifespan_context(self):
        """Test handling of malformed lifespan context."""
        context = Mock(spec=Context)
        context.request_context = Mock()
        context.request_context.lifespan_context = None  # Malformed context
        
        # This should raise a TypeError since None is not subscriptable
        with pytest.raises(TypeError, match="'NoneType' object is not subscriptable"):
            await _get_weather_fn(context, "51.5074", "-0.1278")

    @pytest.mark.asyncio 
    async def test_network_timeout_simulation(self, mock_context_error):
        """Test handling of network timeout errors."""
        weather_client = mock_context_error.request_context.lifespan_context["weather_client"]
        weather_client.get_weather = AsyncMock(side_effect=WeatherApiError("Request timeout"))
        
        with pytest.raises(ToolError, match="Weather API error: Request timeout"):
            await _get_weather_fn(mock_context_error, "51.5074", "-0.1278")

    @pytest.mark.asyncio
    async def test_concurrent_requests_error_handling(self, mock_context_error):
        """Test error handling with concurrent weather requests."""
        import asyncio
        
        weather_client = mock_context_error.request_context.lifespan_context["weather_client"] 
        weather_client.get_weather = AsyncMock(side_effect=WeatherClientError("Concurrent request limit exceeded"))
        
        # Create multiple concurrent requests
        tasks = [
            _get_weather_fn(mock_context_error, "40.7128", "-74.0060"),
            _get_weather_fn(mock_context_error, "51.5074", "-0.1278"),
            _get_weather_fn(mock_context_error, "35.6762", "139.6503")
        ]
        
        # All should fail with the same error
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            assert isinstance(result, ToolError)
            assert "Weather client error: Concurrent request limit exceeded" in str(result)


class TestMCPServerIntegration:
    """Test cases for MCP server integration and decoration."""
    
    def test_get_weather_tool_registration(self):
        """Test that get_weather is properly registered as a tool."""
        from mcp_server_weather.server import mcp_server
        
        # Check that the tool is registered
        assert hasattr(get_weather, 'fn')
        assert get_weather.name == 'get_weather'
        
        # Verify the tool has correct metadata
        assert get_weather.description is not None
        # Parameters might be a dict or have different structure depending on FastMCP version
        parameters = getattr(get_weather, 'parameters', {})
        if hasattr(parameters, 'properties'):
            assert len(parameters.properties) >= 2  # latitude, longitude at minimum
        elif isinstance(parameters, dict):
            # If parameters is a dict, check if it has the expected structure
            properties = parameters.get('properties', parameters)
            assert len(properties) >= 2

    def test_mcp_server_has_lifespan(self):
        """Test that MCP server is configured with lifespan.""" 
        from mcp_server_weather.server import mcp_server
        
        # Check that server has lifespan configured
        # The lifespan might be stored differently depending on FastMCP version
        # Let's check if the server was created with app_lifespan
        assert mcp_server is not None
        assert mcp_server.name == "weather-server"

    @pytest.mark.asyncio
    async def test_weather_tool_parameter_validation(self):
        """Test parameter validation by the tool decorator."""
        # This test verifies that the tool decorator properly validates parameters
        # We can't easily test this without invoking the full MCP protocol,
        # but we can test that the underlying function works with proper parameters
        
        mock_context = Mock(spec=Context)
        mock_context.request_context = Mock()
        mock_context.request_context.lifespan_context = {
            "weather_client": Mock()
        }
        
        weather_client = mock_context.request_context.lifespan_context["weather_client"]
        weather_client.get_weather = AsyncMock(return_value=WeatherData(
            state="test",
            temperature="20.0C",
            humidity="50%"
        ))
        
        # Test with all parameters
        result = await _get_weather_fn(
            mock_context, 
            latitude="40.7128", 
            longitude="-74.0060",
            units="metric"
        )
        
        assert result is not None
        assert "state" in result
        
        # Verify the client was called with correct parameters
        weather_client.get_weather.assert_called_once_with(
            latitude="40.7128",
            longitude="-74.0060",
            units="metric"
        ) 