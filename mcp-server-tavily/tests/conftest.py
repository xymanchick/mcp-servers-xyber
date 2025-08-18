import pytest
from unittest.mock import MagicMock, AsyncMock, patch


@pytest.fixture
def mock_config():
    config = MagicMock()
    config.api_key = "test_api_key"
    config.max_results = 5
    config.topic = "general"
    config.search_depth = "basic"
    config.include_answer = False
    config.include_raw_content = False
    config.include_images = False
    return config


@pytest.fixture
def mock_tavily_tool():
    tool = AsyncMock()
    tool.ainvoke = AsyncMock()
    return tool


@pytest.fixture
def mock_result():
    return {"results": [{"title": "Test", "url": "#", "content": "Test"}]}


@pytest.fixture
def mock_sleep():
    with patch('asyncio.sleep', return_value=None) as mock_async_sleep, \
         patch('time.sleep', return_value=None) as mock_time_sleep:
        yield mock_async_sleep, mock_time_sleep
