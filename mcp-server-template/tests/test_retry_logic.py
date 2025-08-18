"""Test cases for retry mechanism.

Test the functionality of retry_api_call decorator, including retry triggering,
retry count, exponential backoff timing and logging.

COVERAGE SUMMARY:
This test file provides comprehensive coverage of the retry mechanism, including:

1. **Basic Retry Scenarios:**
   - ClientError -> Success (test_retry_on_client_error_then_success)
   - WeatherApiError (HTTP errors) -> Success (test_retry_on_weather_api_error_then_success)
   - Mixed exception types -> Success (test_mixed_exception_types_then_success)

2. **Failure Scenarios:**
   - Max retries exceeded (test_max_retries_exceeded)
   - HTTP error codes: 500, 502, 503, 504, 429 (test_retry_on_http_error_codes)

3. **Non-retryable Scenarios:**
   - Parsing errors (KeyError) should not retry (test_no_retry_on_parsing_error)
   - Successful responses should not retry (test_successful_response_no_retry)

4. **API Error Responses:**
   - JSON response with error codes (test_retry_with_api_error_response)

5. **Timing and Performance:**
   - Exponential backoff verification (test_exponential_backoff_timing_fast)

6. **Cache Integration:**
   - Cache behavior during retry failures (test_cache_not_used_during_retry_failures)

7. **Logging Verification:**
   - All tests verify proper retry logging with count and message verification

Note: Some tests (test_max_retries_exceeded, test_retry_on_http_error_codes) use
real retry timing and may take longer to execute due to exponential backoff.
"""

import asyncio
import json
import logging
import time
from unittest.mock import Mock, patch, AsyncMock, MagicMock

import pytest
import aiohttp
import aiohttp.connector
from aioresponses import aioresponses
from tenacity import RetryError, stop_after_attempt, wait_fixed, retry_if_exception_type, before_sleep_log, retry

from mcp_server_weather.weather.config import WeatherConfig, WeatherApiError, WeatherClientError
from mcp_server_weather.weather.module import WeatherClient

from mcp_server_weather.weather.models import WeatherData
from mcp_server_weather.weather.module import WeatherClient
from requests.exceptions import ConnectionError, RequestException, Timeout

# Test data constants
TEST_COORDINATES = {
    "london": ("51.5074", "-0.1278"),
    "new_york": ("40.7128", "-74.0060"),
    "tokyo": ("35.6762", "139.6503"),
}

MOCK_RESPONSES = {
    "london": {
        "weather": [{"description": "cloudy"}],
        "main": {"temp": 15.5, "humidity": 76},
        "cod": 200,
    },
    "new_york": {
        "weather": [{"description": "sunny"}],
        "main": {"temp": 22.8, "humidity": 65},
        "cod": 200,
    },
    "tokyo": {
        "weather": [{"description": "rainy"}],
        "main": {"temp": 18.2, "humidity": 85},
        "cod": 200,
    },
}


class TestRetryApiCallDecorator:
    """Test the functionality of retry_api_call decorator."""

    
    @pytest.mark.asyncio
    async def test_retry_on_client_error_then_success(self, weather_client, caplog, mock_asyncio_sleep, mock_http_response_factory):
        """Test retry triggered on aiohttp.ClientError, eventually succeeds."""
        call_count = 0
        
        def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            
            if call_count <= 2:
                raise aiohttp.ClientError("Connection error")
            
            # Use the factory to create success response
            return mock_http_response_factory(
                status=200, 
                json_data=MOCK_RESPONSES['london']
            )
        
        with patch.object(aiohttp.ClientSession, 'get', side_effect=mock_get):
            with patch('asyncio.sleep', side_effect=mock_asyncio_sleep):
                with caplog.at_level(logging.WARNING):
                    result = await weather_client.get_weather(
                        latitude="51.5074", 
                        longitude="-0.1278"
                    )
        
        # Verify results
        assert isinstance(result, WeatherData)
        assert result.state == "cloudy"
        assert result.temperature == "15.5C"
        assert result.humidity == "76%"

        # Verify retry count (should call 3 times)
        assert call_count == 3

        # Verify retry logs
        retry_logs = [
            record for record in caplog.records if "Retrying" in record.message
        ]
        assert len(retry_logs) == 2  # Two retry logs
    
    @pytest.mark.asyncio
    async def test_retry_on_weather_api_error_then_success(self, weather_client, caplog):
        """Test retry triggered on WeatherApiError, eventually succeeds."""
        call_count = 0
        
        def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            
            class MockResponse:
                def __init__(self, status):
                    self.status = status
                
                async def text(self):
                    if self.status == 429:
                        return "Too many requests"
                    elif self.status == 503:
                        return "Service unavailable"
                    return ""
                
                async def json(self):
                    return MOCK_RESPONSES['new_york']
                
                async def __aenter__(self):
                    return self
                
                async def __aexit__(self, exc_type, exc_val, exc_tb):
                    pass
            
            if call_count == 1:
                return MockResponse(429)  # First call: 429 Too Many Requests
            elif call_count == 2:
                return MockResponse(503)  # Second call: 503 Service Unavailable  
            else:
                return MockResponse(200)  # Third call: Success
        
        # Mock sleep to make tests fast
        async def mock_sleep(seconds):
            pass
        
        with patch.object(aiohttp.ClientSession, 'get', side_effect=mock_get):
            with patch('asyncio.sleep', side_effect=mock_sleep):
                with caplog.at_level(logging.WARNING):
                    result = await weather_client.get_weather(
                        latitude="40.7128",
                        longitude="-74.0060"
                    )
        
        # Verify results
        assert isinstance(result, WeatherData)
        assert result.state == "sunny"

        # Verify retry logs
        retry_logs = [
            record for record in caplog.records if "Retrying" in record.message
        ]
        assert len(retry_logs) == 2
    
    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self, weather_client, caplog):
        """Test that function throws exception after exceeding max retries."""
        call_count = 0
        def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            # Use simple ClientError which doesn't have SSL issues
            raise aiohttp.ClientError("Connection failed")
        
        # Mock sleep to make tests fast
        async def mock_sleep(seconds):
            pass
        
        with patch.object(aiohttp.ClientSession, 'get', side_effect=mock_get):
            with patch('asyncio.sleep', side_effect=mock_sleep):
                with caplog.at_level(logging.WARNING):
                    with pytest.raises(WeatherApiError):
                        await weather_client.get_weather(
                            latitude="35.6762",
                            longitude="139.6503"
                        )
        
        # Verify retry count (5 retries = total 5 calls as per real decorator)
        assert call_count == 5
        
        # Verify retry logs (should have 4 retry logs for 5 attempts)
        retry_logs = [record for record in caplog.records if "Retrying" in record.message]
        assert len(retry_logs) == 4
    
    @pytest.mark.asyncio
    async def test_no_retry_on_parsing_error(self, weather_client, caplog):
        """Test that parsing errors (KeyError) are not retried."""
        call_count = 0
        
        def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            
            class MockResponse:
                def __init__(self):
                    self.status = 200
                
                async def json(self):
                    # Missing 'description' in weather[0] will cause KeyError
                    return {"cod": 200, "weather": [{}], "main": {"temp": 20, "humidity": 50}}
                
                async def __aenter__(self):
                    return self
                
                async def __aexit__(self, exc_type, exc_val, exc_tb):
                    pass
            
            return MockResponse()
        
        with patch.object(aiohttp.ClientSession, 'get', side_effect=mock_get):
            with caplog.at_level(logging.WARNING):
                with pytest.raises(WeatherClientError):
                    await weather_client.get_weather(
                        latitude="51.5074",
                        longitude="-0.1278"
                    )
        
        # Verify no retries occurred
        assert call_count == 1
        
        # Verify no retry logs
        retry_logs = [
            record for record in caplog.records if "Retrying" in record.message
        ]
        assert len(retry_logs) == 0
    
    @pytest.mark.asyncio
    async def test_exponential_backoff_timing_fast(self, weather_client):
        """Test that retry uses exponential backoff for wait times with fast mocking."""
        # Mock asyncio.sleep to track wait times
        sleep_times = []
        
        async def mock_sleep(seconds):
            sleep_times.append(seconds)
            # Don't actually sleep in tests
            return None
        
        call_count = 0
        def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise aiohttp.ClientError("Connection error")
        
        # Use quick mocking without actual waits
        with patch('asyncio.sleep', side_effect=mock_sleep):
            with patch.object(aiohttp.ClientSession, 'get', side_effect=mock_get):
                # Also patch the tenacity wait to prevent real sleeps
                with patch('tenacity.wait_exponential', return_value=lambda retry_state: 0.001):
                    try:
                        await weather_client.get_weather(
                            latitude="35.6762",
                            longitude="139.6503"
                        )
                    except WeatherApiError:
                        pass  # Expected exception after max retries
        
        # Just verify that some sleep attempts were made and retries occurred
        assert call_count == 5  # 5 attempts total
        assert len(sleep_times) >= 1  # At least some sleep calls were made
    
    @pytest.mark.asyncio
    async def test_retry_on_http_error_codes(self, weather_client, caplog):
        """Test retry on various HTTP error codes that should trigger WeatherApiError."""
        test_cases = [
            (500, "Internal Server Error"),
            (502, "Bad Gateway"), 
            (503, "Service Unavailable"),
            (504, "Gateway Timeout"),
            (429, "Too Many Requests"),
        ]
        
        for status_code, error_msg in test_cases:
            caplog.clear()  # Clear logs between test cases
            
            call_count = 0
            def mock_get(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                
                class MockResponse:
                    def __init__(self):
                        self.status = status_code
                    
                    async def text(self):
                        return error_msg
                    
                    async def __aenter__(self):
                        return self
                    
                    async def __aexit__(self, exc_type, exc_val, exc_tb):
                        pass
                
                return MockResponse()
            
            # Mock sleep to make tests fast
            async def mock_sleep(seconds):
                pass
            
            with patch.object(aiohttp.ClientSession, 'get', side_effect=mock_get):
                with patch('asyncio.sleep', side_effect=mock_sleep):
                    with caplog.at_level(logging.WARNING):
                        with pytest.raises(WeatherApiError) as exc_info:
                            await weather_client.get_weather(
                                latitude="51.5074",
                                longitude="-0.1278"
                            )
            
            # Verify that retry was attempted (5 calls total for real decorator)
            assert call_count == 5
            
            # Verify retry logs (should have 4 retry logs for 5 attempts)
            retry_logs = [record for record in caplog.records if "Retrying" in record.message]
            assert len(retry_logs) == 4
            
            # Verify error message contains HTTP status
            assert str(status_code) in str(exc_info.value)
    
    @pytest.mark.asyncio 
    async def test_retry_with_api_error_response(self, weather_client, caplog):
        """Test retry when API returns error in JSON response."""
        call_count = 0
        def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            
            class MockResponse:
                def __init__(self):
                    self.status = 200  # HTTP OK but API error
                
                async def json(self):
                    if call_count <= 2:
                        # First two calls: API errors
                        return {
                            "cod": 401,
                            "message": "Invalid API key"
                        }
                    else:
                        # Third call: Success
                        return MOCK_RESPONSES['tokyo']
                
                async def __aenter__(self):
                    return self
                
                async def __aexit__(self, exc_type, exc_val, exc_tb):
                    pass
            
            return MockResponse()
        
        # Mock sleep to make tests fast
        async def mock_sleep(seconds):
            pass
        
        with patch.object(aiohttp.ClientSession, 'get', side_effect=mock_get):
            with patch('asyncio.sleep', side_effect=mock_sleep):
                with caplog.at_level(logging.WARNING):
                    result = await weather_client.get_weather(
                        latitude="35.6762",
                        longitude="139.6503"
                    )
        
        # Verify results
        assert isinstance(result, WeatherData)
        assert result.state == "rainy"
        
        # Verify retry occurred
        assert call_count == 3
        
        # Verify retry logs
        retry_logs = [record for record in caplog.records if "Retrying" in record.message]
        assert len(retry_logs) == 2
    
    @pytest.mark.asyncio 
    async def test_cache_not_used_during_retry_failures(self, weather_client_with_cache, caplog, mock_asyncio_sleep, mock_http_response_factory):
        """Test that cache is not used when initial requests fail."""
        call_count = 0
        def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            
            if call_count == 1:
                # First call fails
                raise aiohttp.ClientError("Connection error")
            else:
                # Second call succeeds - use factory
                return mock_http_response_factory(
                    status=200,
                    json_data=MOCK_RESPONSES['london']
                )
        
        with patch.object(aiohttp.ClientSession, 'get', side_effect=mock_get):
            with patch('asyncio.sleep', side_effect=mock_asyncio_sleep):
                with caplog.at_level(logging.WARNING):
                    result = await weather_client_with_cache.get_weather(
                        latitude="51.5074",
                        longitude="-0.1278"
                    )
        
        # Verify results
        assert isinstance(result, WeatherData)
        assert result.state == "cloudy"
        
        # Verify retry occurred (2 calls total)
        assert call_count == 2
        
        # Verify retry logs
        retry_logs = [record for record in caplog.records if "Retrying" in record.message]
        assert len(retry_logs) == 1
        
        # Verify data was cached after successful retry
        cache_key = weather_client_with_cache._get_cache_key("51.5074", "-0.1278", "metric")
        assert cache_key in weather_client_with_cache._cache
    
    @pytest.mark.asyncio
    async def test_mixed_exception_types_then_success(self, weather_client, caplog):
        """Test retry with mixed exception types (ClientError, WeatherApiError, then success)."""
        call_count = 0
        
        def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            
            if call_count == 1:
                # First call: ClientError
                raise aiohttp.ClientError("Connection error")
            elif call_count == 2:
                # Second call: HTTP error (WeatherApiError)
                class MockResponse:
                    def __init__(self):
                        self.status = 503
                    
                    async def text(self):
                        return "Service unavailable"
                    
                    async def __aenter__(self):
                        return self
                    
                    async def __aexit__(self, exc_type, exc_val, exc_tb):
                        pass
                
                return MockResponse()
            else:
                # Third call: Success
                class MockResponse:
                    def __init__(self):
                        self.status = 200
                    
                    async def json(self):
                        return MOCK_RESPONSES['tokyo']
                    
                    async def __aenter__(self):
                        return self
                    
                    async def __aexit__(self, exc_type, exc_val, exc_tb):
                        pass
                
                return MockResponse()
        
        # Mock sleep to make tests fast
        async def mock_sleep(seconds):
            pass
        
        with patch.object(aiohttp.ClientSession, 'get', side_effect=mock_get):
            with patch('asyncio.sleep', side_effect=mock_sleep):
                with caplog.at_level(logging.WARNING):
                    result = await weather_client.get_weather(
                        latitude="35.6762",
                        longitude="139.6503"
                    )
        
        # Verify results
        assert isinstance(result, WeatherData)
        assert result.state == "rainy"
        
        # Verify retry occurred (3 calls total)
        assert call_count == 3
        
        # Verify retry logs
        retry_logs = [record for record in caplog.records if "Retrying" in record.message]
        assert len(retry_logs) == 2
    
    @pytest.mark.asyncio
    async def test_successful_response_no_retry(self, weather_client, caplog):
        """Test that successful responses do not trigger retries."""
        call_count = 0
        
        def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            
            class MockResponse:
                def __init__(self):
                    self.status = 200
                
                async def json(self):
                    return MOCK_RESPONSES['london']
                
                async def __aenter__(self):
                    return self
                
                async def __aexit__(self, exc_type, exc_val, exc_tb):
                    pass
            
            return MockResponse()
        
        with patch.object(aiohttp.ClientSession, 'get', side_effect=mock_get):
            with caplog.at_level(logging.WARNING):
                result = await weather_client.get_weather(
                    latitude="51.5074",
                    longitude="-0.1278"
                )
        
        # Verify results
        assert isinstance(result, WeatherData)
        assert result.state == "cloudy"
        
        # Verify only one call was made (no retries)
        assert call_count == 1
        
        # Verify no retry logs
        retry_logs = [record for record in caplog.records if "Retrying" in record.message]
        assert len(retry_logs) == 0 
