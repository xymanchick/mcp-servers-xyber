import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest
from mcp_server_tavily.tavily.module import _TavilyService

MOCK_RESULT = {"results": [{"title": "Test", "url": "#", "content": "Test"}]}


@pytest.fixture
def mock_config():
    config = MagicMock()
    config.api_key = "test_api_key"
    return config


@pytest.mark.asyncio
async def test_search_retries_on_timeout(mock_config, mocker, caplog):
    tavily_service = _TavilyService(mock_config)
    mock_tavily_tool = AsyncMock()

    # Mock results from Tavily search
    mock_tavily_tool.ainvoke.side_effect = [asyncio.TimeoutError(), MOCK_RESULT]

    mocker.patch.object(
        tavily_service, "_create_tavily_tool", return_value=mock_tavily_tool
    )
    caplog.set_level(logging.WARNING)

    response = await tavily_service.search("Test")

    # Check that search is called until the result is returned
    assert response[0].title == "Test"
    assert mock_tavily_tool.ainvoke.call_count == 2

    # Check that each failed call yields a warning
    logs = [rec for rec in caplog.records if rec.levelno == logging.WARNING]
    assert len(logs) == 1
    assert any("TimeoutError")


@pytest.mark.asyncio
async def test_search_retries_on_recoverable_http_error(mock_config, mocker):
    tavily_service = _TavilyService(mock_config)
    mock_tavily_tool = AsyncMock()

    # Mock results from Tavily search
    mock_tavily_tool.ainvoke.side_effect = [
        Exception("Error 429: Too Many Requests"),
        Exception("Error 500: Internal Server Error"),
        Exception("Error 501: Internal Server Error"),
        MOCK_RESULT,
    ]

    mocker.patch.object(
        tavily_service, "_create_tavily_tool", return_value=mock_tavily_tool
    )

    response = await tavily_service.search("Test")

    # Check that search is called until the result is returned
    assert response[0].title == "Test"
    assert mock_tavily_tool.ainvoke.call_count == 4


@pytest.mark.asyncio
async def test_search_fails_on_client_error(mock_config, mocker):
    tavily_service = _TavilyService(mock_config)
    mock_tavily_tool = AsyncMock()

    # Mock results from Tavily search
    mock_tavily_tool.ainvoke.side_effect = [aiohttp.ClientError(), MOCK_RESULT]

    mocker.patch.object(
        tavily_service, "_create_tavily_tool", return_value=mock_tavily_tool
    )

    response = await tavily_service.search("Test")

    # Check that search is called until the result is returned
    assert response[0].title == "Test"
    assert mock_tavily_tool.ainvoke.call_count == 2


@pytest.mark.asyncio
async def test_search_fails_on_unrecoverable_http_error(mock_config, mocker):
    tavily_service = _TavilyService(mock_config)
    mock_tavily_tool = AsyncMock()

    # Mock results from Tavily search
    mock_tavily_tool.ainvoke.side_effect = [
        Exception("Error 400: Bad Request"),
        MOCK_RESULT,
    ]

    mocker.patch.object(
        tavily_service, "_create_tavily_tool", return_value=mock_tavily_tool
    )

    response = await tavily_service.search("Test")

    assert response[0].title == "Search Error"
    assert mock_tavily_tool.ainvoke.call_count == 1


@pytest.mark.asyncio
async def test_search_fails_after_five_attempts(mock_config, mocker):
    tavily_service = _TavilyService(mock_config)
    mock_tavily_tool = AsyncMock()

    # Mock results from Tavily search
    mock_tavily_tool.ainvoke.side_effect = aiohttp.ClientError("Persistent Failure")

    mocker.patch.object(
        tavily_service, "_create_tavily_tool", return_value=mock_tavily_tool
    )

    response = await tavily_service.search("Test")

    assert response[0].title == "Search Error"
    assert mock_tavily_tool.ainvoke.call_count == 5
