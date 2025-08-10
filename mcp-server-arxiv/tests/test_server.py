from contextlib import nullcontext as not_rise_error
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from mcp_server_arxiv import (
    ArxivApiError,
    ArxivConfigError,
    ArxivSearchResult,
    ArxivServiceError,
)
from mcp_server_arxiv.server import app_lifespan, mcp_server


@pytest.mark.asyncio
@patch("mcp_server_arxiv.server.get_arxiv_service", return_value=MagicMock(name="_ArxivService"))
@patch("mcp_server_arxiv.server.logger")
async def test_app_lifespan_success(mock_logger, mock_get_service):

    async with app_lifespan(mcp_server) as lifespan_ctx:
        assert "arxiv_service" in lifespan_ctx
        assert lifespan_ctx["arxiv_service"] is mock_get_service.return_value

    mock_logger.info.assert_any_call("Lifespan: Initializing services...")
    mock_logger.info.assert_any_call("Lifespan: Services initialized successfully")
    mock_logger.info.assert_any_call("Lifespan: Shutdown cleanup completed")



@pytest.mark.asyncio
@patch("mcp_server_arxiv.server.get_arxiv_service", side_effect=ArxivConfigError("config error"))
@patch("mcp_server_arxiv.server.logger")
async def test_app_lifespan_raises_arxiv_config_error(mock_logger, mock_get_service):
    with pytest.raises(ArxivConfigError, match="config error"):
        async with app_lifespan(mcp_server):
            pass

    mock_logger.error.assert_called()
    err_msg = mock_logger.error.call_args[0][0]
    assert "Lifespan initialization failed" in err_msg
    mock_logger.info.assert_any_call("Lifespan: Shutdown cleanup completed")


@pytest.mark.asyncio
@patch("mcp_server_arxiv.server.get_arxiv_service", side_effect=ArxivServiceError("service error"))
@patch("mcp_server_arxiv.server.logger")
async def test_app_lifespan_raises_arxiv_service_error(mock_logger, mock_get_service):
    with pytest.raises(ArxivServiceError, match="service error"):
        async with app_lifespan(mcp_server):
            pass

    mock_logger.error.assert_called()
    err_msg = mock_logger.error.call_args[0][0]
    assert "Lifespan initialization failed" in err_msg
    mock_logger.info.assert_any_call("Lifespan: Shutdown cleanup completed")


@pytest.mark.asyncio
@patch("mcp_server_arxiv.server.get_arxiv_service", side_effect=RuntimeError("unexpected error"))
@patch("mcp_server_arxiv.server.logger")
async def test_app_lifespan_raises_unexpected_error(mock_logger, mock_get_service):
    with pytest.raises(RuntimeError, match="unexpected error"):
        async with app_lifespan(mcp_server):
            pass

    mock_logger.error.assert_called()
    err_msg = mock_logger.error.call_args[0][0]
    assert "Unexpected error during lifespan initialization" in err_msg
    mock_logger.info.assert_any_call("Lifespan: Shutdown cleanup completed")



@pytest.mark.asyncio
@patch("mcp_server_arxiv.server.logger")
@patch("mcp_server_arxiv.server.get_arxiv_service")
async def test_arxiv_search_success(mock_get_arxiv_service, mock_logger, mcp_server_fixture, sample_arxiv_search_result):
    # Create a new result with str method mocked via patch instead of assignment
    fake_result = sample_arxiv_search_result

    fake_arxiv_service = MagicMock()
    fake_arxiv_service.search = AsyncMock(return_value=[fake_result])

    mock_get_arxiv_service.return_value = fake_arxiv_service

    request_data = {
        "query": "quantum computing",
        "max_results": 1,
        "max_text_length": 2000,
    }

    async with Client(mcp_server_fixture) as client:
        response = await client.call_tool("arxiv_search", request_data)

    assert "ArXiv Search Results:" in response.data
    assert "Title: Test Paper" in response.data
    assert "Authors: Test Author" in response.data

    fake_arxiv_service.search.assert_awaited_once_with(
        query="quantum computing",
        max_results_override=1,
        max_text_length_override=2000,
    )


@pytest.mark.asyncio
@pytest.mark.asyncio
@patch("mcp_server_arxiv.server.logger")
@patch("mcp_server_arxiv.server.get_arxiv_service")
async def test_arxiv_search_errors(
    mock_get_arxiv_service, mock_logger, mcp_server_fixture, 
    arxiv_api_error, sample_arxiv_search_result
):
    
    fake_arxiv_service = MagicMock()
    fake_arxiv_service.search = AsyncMock(side_effect=arxiv_api_error)
    mock_get_arxiv_service.return_value = fake_arxiv_service

    request_data = {
        "query": "quantum computing",
        "max_results": 1,
        "max_text_length": 1000,
    }

    async with Client(mcp_server_fixture) as client:
        with pytest.raises(ToolError, match="ArXiv API error"):
            await client.call_tool("arxiv_search", request_data)


@pytest.mark.asyncio
@patch("mcp_server_arxiv.server.logger")
@patch("mcp_server_arxiv.server.get_arxiv_service")
async def test_arxiv_search_service_error(mock_get_arxiv_service, mock_logger, mcp_server_fixture):
    """Test ArxivServiceError handling."""
    fake_arxiv_service = MagicMock()
    fake_arxiv_service.search = AsyncMock(side_effect=ArxivServiceError("Service failure"))
    mock_get_arxiv_service.return_value = fake_arxiv_service

    request_data = {"query": "test", "max_results": 1}

    async with Client(mcp_server_fixture) as client:
        with pytest.raises(ToolError, match="ArXiv service error"):
            await client.call_tool("arxiv_search", request_data)


@pytest.mark.asyncio
@patch("mcp_server_arxiv.server.logger")
@patch("mcp_server_arxiv.server.get_arxiv_service")
async def test_arxiv_search_value_error(mock_get_arxiv_service, mock_logger, mcp_server_fixture):
    fake_arxiv_service = MagicMock()
    fake_arxiv_service.search = AsyncMock(side_effect=ValueError("Invalid input"))
    mock_get_arxiv_service.return_value = fake_arxiv_service

    request_data = {"query": "", "max_results": 1}

    async with Client(mcp_server_fixture) as client:
        with pytest.raises(ToolError, match="Input validation error"):
            await client.call_tool("arxiv_search", request_data)


@pytest.mark.asyncio
@patch("mcp_server_arxiv.server.logger")
@patch("mcp_server_arxiv.server.get_arxiv_service")
async def test_arxiv_search_empty_results(mock_get_arxiv_service, mock_logger, mcp_server_fixture):
    fake_arxiv_service = MagicMock()
    fake_arxiv_service.search = AsyncMock(return_value=[])  # Empty results
    
    mock_get_arxiv_service.return_value = fake_arxiv_service

    request_data = {
        "query": "nonexistent quantum paper xyz123",
        "max_results": 5,
    }

    async with Client(mcp_server_fixture) as client:
        response = await client.call_tool("arxiv_search", request_data)

    assert response.data == "No relevant papers found or processed on arXiv for the given query"
    
    fake_arxiv_service.search.assert_awaited_once_with(
        query="nonexistent quantum paper xyz123",
        max_results_override=5,
        max_text_length_override=None,
    )
    
    mock_logger.info.assert_any_call(
        "No relevant papers found or processed on arXiv for the given query"
    )


@pytest.mark.asyncio
@patch("mcp_server_arxiv.server.logger")
@patch("mcp_server_arxiv.server.get_arxiv_service")
async def test_arxiv_search_with_default_parameters(mock_get_arxiv_service, mock_logger, mcp_server_fixture):
    fake_result = MagicMock(spec=ArxivSearchResult)
    fake_result.__str__.return_value = "Test Paper - Test Author"

    fake_arxiv_service = MagicMock()
    fake_arxiv_service.search = AsyncMock(return_value=[fake_result])
    
    mock_get_arxiv_service.return_value = fake_arxiv_service

    request_data = {"query": "machine learning"}

    async with Client(mcp_server_fixture) as client:
        response = await client.call_tool("arxiv_search", request_data)

    assert "ArXiv Search Results:" in response.data
    assert "Test Paper - Test Author" in response.data
    
    fake_arxiv_service.search.assert_awaited_once_with(
        query="machine learning",
        max_results_override=None,
        max_text_length_override=None,
    )


@pytest.mark.asyncio
@patch("mcp_server_arxiv.server.logger")
@patch("mcp_server_arxiv.server.get_arxiv_service")
async def test_arxiv_search_multiple_results_formatting(mock_get_arxiv_service, mock_logger, mcp_server_fixture):
    fake_result1 = MagicMock(spec=ArxivSearchResult)
    fake_result1.__str__.return_value = "First Paper - First Author"
    
    fake_result2 = MagicMock(spec=ArxivSearchResult)
    fake_result2.__str__.return_value = "Second Paper - Second Author"

    fake_arxiv_service = MagicMock()
    fake_arxiv_service.search = AsyncMock(return_value=[fake_result1, fake_result2])
    
    mock_get_arxiv_service.return_value = fake_arxiv_service

    request_data = {"query": "deep learning", "max_results": 2}

    async with Client(mcp_server_fixture) as client:
        response = await client.call_tool("arxiv_search", request_data)

    assert "ArXiv Search Results:" in response.data
    assert "--- Paper 1 ---" in response.data
    assert "--- Paper 2 ---" in response.data
    assert "First Paper - First Author" in response.data
    assert "Second Paper - Second Author" in response.data
    
    mock_logger.info.assert_any_call(
        "Successfully processed search request. Returning 2 formatted ArXiv results"
    )


@pytest.mark.asyncio
async def test_mcp_server_tool_registration():
    async with Client(mcp_server) as client:
        tools = await client.list_tools()
    
    tool_names = [tool.name for tool in tools]
    assert "arxiv_search" in tool_names
    
    arxiv_tool = next(tool for tool in tools if tool.name == "arxiv_search")
    
    assert "query" in arxiv_tool.inputSchema["properties"]
    assert arxiv_tool.inputSchema["required"] == ["query"]
    
    assert "max_results" in arxiv_tool.inputSchema["properties"]
    assert "max_text_length" in arxiv_tool.inputSchema["properties"]