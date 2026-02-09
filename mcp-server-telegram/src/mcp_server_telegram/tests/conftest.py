from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import Request
from fastmcp import Context


class MockTelegramConfig:
    def __init__(self, token="test_token", channel="@test_channel"):
        self.token = token
        self.channel = channel


@pytest.fixture
def mock_config():
    return MockTelegramConfig()


@pytest.fixture
def mock_config_empty_token():
    return MockTelegramConfig(token="")


@pytest.fixture
def mock_config_empty_channel():
    return MockTelegramConfig(channel="")


@pytest.fixture
def mock_config_empty_both():
    return MockTelegramConfig(token="", channel="")


@pytest.fixture
def mock_success_response():
    response = Mock()
    response.status_code = 200
    response.raise_for_status.return_value = None
    return response


@pytest.fixture
def mock_400_parse_error_response():
    response = Mock()
    response.status_code = 400
    response.json.return_value = {"description": "Bad Request: can't parse entities"}
    return response


@pytest.fixture
def mock_400_other_error_response():
    response = Mock()
    response.status_code = 400
    response.json.return_value = {"description": "Bad Request: chat not found"}
    return response


@pytest.fixture
def mock_401_error_response():
    response = Mock()
    response.status_code = 401
    response.json.return_value = {"description": "Unauthorized"}
    return response


@pytest.fixture
def mock_500_error_response():
    response = Mock()
    response.status_code = 500
    response.text = "Internal Server Error"
    return response


@pytest.fixture
def create_mock_config():
    def _create_config(token="test_token", channel="@test_channel"):
        return MockTelegramConfig(token=token, channel=channel)

    return _create_config


@pytest.fixture
def mock_request():
    request = Mock(spec=Request)
    request.headers = {}
    return request


@pytest.fixture
def mock_context(mock_request):
    context = Mock(spec=Context)
    context.request_context = Mock()
    context.request_context.request = mock_request
    return context


@pytest.fixture
def mock_telegram_service():
    service = Mock()
    service.send_message = AsyncMock()
    return service
