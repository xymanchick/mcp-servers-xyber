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
async def test_arxiv_search_success(mock_get_arxiv_service, mock_logger, mcp_server_fixture):
    fake_result = MagicMock(spec=ArxivSearchResult)
    fake_result.__str__.return_value = "Paper Title - Author"

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
    assert "Paper Title - Author" in response.data

    fake_arxiv_service.search.assert_awaited_once_with(
        query="quantum computing",
        max_results_override=1,
        max_text_length_override=2000,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ["error_ctx", "side_effect", "expected_exception", "match"],
    [
        (pytest.raises(ToolError, match="Input validation error: Invalid input"), ValueError("Invalid input"), ToolError, "Input validation error"),
        (pytest.raises(ToolError, match="ArXiv API error: API failure"), ArxivApiError("API failure"), ToolError,"ArXiv API error"),
        (pytest.raises(ToolError, match="ArXiv service error: Service failure"), ArxivServiceError("Service failure"), ToolError, "ArXiv service error"),
        (pytest.raises(ToolError, match="An unexpected error occurred during search."), Exception("Unexpected"), ToolError, "unexpected error"),
        (not_rise_error(), None, None, None),
    ],
    ids=["value_error", "api_error", "service_error", "unexpected_error", "success"]
)
@patch("mcp_server_arxiv.server.logger")
@patch("mcp_server_arxiv.server.get_arxiv_service")
async def test_arxiv_search_errors(
    mock_get_arxiv_service, mock_logger, mcp_server_fixture,
    error_ctx, side_effect, expected_exception, match
):
    fake_result = MagicMock()
    fake_result.__str__.return_value = "Paper Title - Author"

    fake_arxiv_service = MagicMock()
    if side_effect is None:
        fake_arxiv_service.search = AsyncMock(return_value=[fake_result])
    else:
        fake_arxiv_service.search = AsyncMock(side_effect=side_effect)

    mock_get_arxiv_service.return_value = fake_arxiv_service

    request_data = {
        "query": "quantum computing",
        "max_results": 1,
        "max_text_length": 1000,
    }

    with error_ctx:
        async with Client(mcp_server_fixture) as client:
            result = await client.call_tool("arxiv_search", request_data)
            if expected_exception is None:
                assert result is not None