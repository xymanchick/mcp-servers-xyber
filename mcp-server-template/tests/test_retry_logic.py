"""Test cases for retry mechanism.

Test the functionality of retry_api_call decorator, including retry triggering,
retry count, exponential backoff timing and logging.
"""
import logging
import time
from unittest.mock import Mock, patch, MagicMock

import pytest
import requests
from requests.exceptions import RequestException, Timeout, ConnectionError

from mcp_server_weather.weather.config import WeatherConfig, WeatherApiError, WeatherClientError
from mcp_server_weather.weather.module import WeatherClient
from mcp_server_weather.weather.models import WeatherData


# Test data constants
TEST_COORDINATES = {
    'london': ('51.5074', '-0.1278'),
    'new_york': ('40.7128', '-74.0060'),
    'tokyo': ('35.6762', '139.6503'),
}

MOCK_RESPONSES = {
    'london': {
        'weather': [{'description': 'cloudy'}],
        'main': {'temp': 15.5, 'humidity': 76},
        'cod': 200
    },
    'new_york': {
        'weather': [{'description': 'sunny'}],
        'main': {'temp': 22.8, 'humidity': 65},
        'cod': 200
    },
    'tokyo': {
        'weather': [{'description': 'rainy'}],
        'main': {'temp': 18.2, 'humidity': 85},
        'cod': 200
    }
}


class TestRetryApiCallDecorator:
    """Test the functionality of retry_api_call decorator."""
    
    @pytest.fixture
    def weather_client(self):
        """Create WeatherClient instance for testing."""
        config = Mock(spec=WeatherConfig)
        config.api_key = "test_api_key"
        config.default_latitude = "51.5074"
        config.default_longitude = "-0.1278"
        config.units = "metric"
        config.timeout_seconds = 5
        config.enable_caching = False  # Disable caching for tests
        
        client = WeatherClient(config)
        return client
    
    def test_retry_on_request_exception_then_success(self, weather_client, caplog):
        """Test retry triggered on RequestException, eventually succeeds."""
        # Create mock response
        mock_response = Mock()
        mock_response.json.return_value = MOCK_RESPONSES['london']
        mock_response.status_code = 200
        
        # Mock requests.get call count
        call_count = 0
        def mock_get_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise RequestException("Connection error")
            return mock_response
        
        with patch('requests.get', side_effect=mock_get_side_effect) as mock_get:
            with caplog.at_level(logging.WARNING):
                result = weather_client.get_weather()
        
        # Verify results
        assert isinstance(result, WeatherData)
        assert result.state == "cloudy"
        assert result.temperature == "15.5C"
        assert result.humidity == "76%"
        
        # Verify retry count (should call 3 times)
        assert call_count == 3
        
        # Verify retry logs
        retry_logs = [record for record in caplog.records if "Retrying" in record.message]
        assert len(retry_logs) == 2  # Two retry logs
        assert "get_weather" in retry_logs[0].message
        assert "RequestException" in retry_logs[0].message
    
    def test_retry_on_weather_api_error_then_success(self, weather_client, caplog):
        """Test retry triggered on WeatherApiError, eventually succeeds."""
        # Mock responses: first two fail, third succeeds
        responses = [
            Mock(status_code=429, json=lambda: {"cod": 429, "message": "Too many requests"}),
            Mock(status_code=503, json=lambda: {"cod": 503, "message": "Service unavailable"}),
            Mock(status_code=200, json=lambda: MOCK_RESPONSES['new_york']),
        ]
        
        with patch('requests.get', side_effect=responses) as mock_get:
            with caplog.at_level(logging.WARNING):
                result = weather_client.get_weather()
        
        # Verify results
        assert isinstance(result, WeatherData)
        assert result.state == "sunny"
        
        # Verify retry logs
        retry_logs = [record for record in caplog.records if "Retrying" in record.message]
        assert len(retry_logs) == 2
    
    def test_max_retries_exceeded(self, weather_client, caplog):
        """Test that function throws exception after exceeding max retries."""
        # Mock persistent failing requests
        with patch('requests.get', side_effect=ConnectionError("Connection failed")) as mock_get:
            with caplog.at_level(logging.WARNING):
                with pytest.raises(WeatherApiError):
                    weather_client.get_weather()
        
        # Verify retry count (5 retries = total 5 calls)
        assert mock_get.call_count == 5
        
        # Verify retry logs (should have 4 retry logs)
        retry_logs = [record for record in caplog.records if "Retrying" in record.message]
        assert len(retry_logs) == 4
    
    def test_no_retry_on_parsing_error(self, weather_client, caplog):
        """Test that parsing errors (KeyError) are not retried."""
        # Create a response that will cause a KeyError during parsing
        mock_response = Mock()
        mock_response.json.return_value = {"cod": 200, "weather": []}  # Missing description
        mock_response.status_code = 200
        
        with patch('requests.get', return_value=mock_response) as mock_get:
            with caplog.at_level(logging.WARNING):
                with pytest.raises(WeatherClientError):
                    weather_client.get_weather()
        
        # Verify no retries occurred
        assert mock_get.call_count == 1
        
        # Verify no retry logs
        retry_logs = [record for record in caplog.records if "Retrying" in record.message]
        assert len(retry_logs) == 0
    
    def test_exponential_backoff_timing(self, weather_client):
        """Test that retry uses exponential backoff for wait times."""
        # Mock time.sleep to track wait times
        sleep_times = []
        original_sleep = time.sleep
        
        def mock_sleep(seconds):
            sleep_times.append(seconds)
            # Don't actually sleep in tests
            return None
        
        # Mock persistent failing requests
        with patch('time.sleep', side_effect=mock_sleep):
            with patch('requests.get', side_effect=RequestException("Connection error")):
                try:
                    weather_client.get_weather()
                except WeatherApiError:
                    pass  # Expected exception after max retries
        
        # Verify exponential backoff pattern (should increase)
        assert len(sleep_times) == 4  # 4 retries = 4 sleeps
        assert sleep_times[0] < sleep_times[1] < sleep_times[2] < sleep_times[3]
        
        # Verify multiplier is around 0.5 (with jitter)
        # First wait should be close to 0.5 seconds
        assert 0.3 <= sleep_times[0] <= 0.7 