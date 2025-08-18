"""Test fixtures for mcp-server-weather."""

import json
from unittest.mock import Mock, patch

import pytest
from mcp_server_weather.weather.config import WeatherConfig
from mcp_server_weather.weather.models import WeatherData


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
