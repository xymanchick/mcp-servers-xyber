import pytest
import logging
from unittest.mock import AsyncMock, MagicMock, patch, call
from contextlib import asynccontextmanager
from typing import Any

from fastmcp import FastMCP, Context
from fastmcp.exceptions import ToolError

from mcp_server_tavily.server import app_lifespan, mcp_server, tavily_web_search
from mcp_server_tavily.tavily import (
    TavilySearchResult,
    TavilyServiceError,
    _TavilyService,
)


class TestAppLifespan:
    @pytest.mark.asyncio
    async def test_app_lifespan_success(self):
        mock_server = MagicMock(spec=FastMCP)
        mock_tavily_service = MagicMock(spec=_TavilyService)
        
        with patch('mcp_server_tavily.server.get_tavily_service', return_value=mock_tavily_service):
            async with app_lifespan(mock_server) as context:
                assert "tavily_service" in context
                assert context["tavily_service"] == mock_tavily_service

    @pytest.mark.asyncio
    async def test_app_lifespan_tavily_service_error(self):
        mock_server = MagicMock(spec=FastMCP)
        
        with patch('mcp_server_tavily.server.get_tavily_service', 
                  side_effect=TavilyServiceError("Config error")):
            with pytest.raises(TavilyServiceError, match="Config error"):
                async with app_lifespan(mock_server):
                    pass

    @pytest.mark.asyncio
    async def test_app_lifespan_unexpected_error(self):
        mock_server = MagicMock(spec=FastMCP)
        
        with patch('mcp_server_tavily.server.get_tavily_service', 
                  side_effect=RuntimeError("Unexpected error")):
            with pytest.raises(RuntimeError, match="Unexpected error"):
                async with app_lifespan(mock_server):
                    pass

    @pytest.mark.asyncio
    async def test_app_lifespan_logging(self, caplog):
        mock_server = MagicMock(spec=FastMCP)
        mock_tavily_service = MagicMock(spec=_TavilyService)
        
        with caplog.at_level(logging.INFO):
            with patch('mcp_server_tavily.server.get_tavily_service', return_value=mock_tavily_service):
                async with app_lifespan(mock_server):
                    pass
        
        log_messages = [record.message for record in caplog.records]
        assert "Lifespan: Initializing services..." in log_messages
        assert "Lifespan: Services initialized successfully" in log_messages
        assert "Lifespan: Shutdown cleanup completed" in log_messages


class TestMcpServerInitialization:
    def test_mcp_server_initialization(self):
        assert isinstance(mcp_server, FastMCP)
        assert mcp_server.name == "tavily"
        assert mcp_server is not None


class TestTavilyWebSearch:
    @pytest.fixture
    def mock_context(self):
        mock_tavily_service = AsyncMock(spec=_TavilyService)
        
        context = MagicMock(spec=Context)
        context.request_context.lifespan_context = {
            "tavily_service": mock_tavily_service
        }
        return context

    @pytest.fixture
    def sample_search_results(self):
        return [
            TavilySearchResult(
                title="Test Result 1",
                url="https://example.com/1",
                content="This is test content 1"
            ),
            TavilySearchResult(
                title="Test Result 2", 
                url="https://example.com/2",
                content="This is test content 2"
            )
        ]

    @pytest.mark.asyncio
    async def test_tavily_web_search_success(self, mock_context, sample_search_results):
        mock_context.request_context.lifespan_context["tavily_service"].search.return_value = sample_search_results
        
        result = await tavily_web_search.fn(mock_context, "test query")
        
        mock_context.request_context.lifespan_context["tavily_service"].search.assert_called_once_with(
            query="test query", max_results=None
        )
        
        expected_response = "\n\n".join([str(result) for result in sample_search_results])
        assert result == expected_response

    @pytest.mark.asyncio
    async def test_tavily_web_search_with_max_results(self, mock_context, sample_search_results):
        mock_context.request_context.lifespan_context["tavily_service"].search.return_value = sample_search_results
        
        result = await tavily_web_search.fn(mock_context, "test query", max_results=3)
        
        mock_context.request_context.lifespan_context["tavily_service"].search.assert_called_once_with(
            query="test query", max_results=3
        )
        
        expected_response = "\n\n".join([str(result) for result in sample_search_results])
        assert result == expected_response

    @pytest.mark.asyncio
    async def test_tavily_web_search_value_error(self, mock_context):
        mock_context.request_context.lifespan_context["tavily_service"].search.side_effect = ValueError("Invalid query")
        
        with pytest.raises(ToolError, match="Input validation error: Invalid query"):
            await tavily_web_search.fn(mock_context, "")

    @pytest.mark.asyncio
    async def test_tavily_web_search_service_error(self, mock_context):
        mock_context.request_context.lifespan_context["tavily_service"].search.side_effect = TavilyServiceError("API error")
        
        with pytest.raises(ToolError, match="Tavily service error: API error"):
            await tavily_web_search.fn(mock_context, "test query")

    @pytest.mark.asyncio
    async def test_tavily_web_search_unexpected_error(self, mock_context):
        mock_context.request_context.lifespan_context["tavily_service"].search.side_effect = RuntimeError("Unexpected error")
        
        with pytest.raises(ToolError, match="An unexpected error occurred during search."):
            await tavily_web_search.fn(mock_context, "test query")

    @pytest.mark.asyncio
    async def test_tavily_web_search_empty_results(self, mock_context):
        mock_context.request_context.lifespan_context["tavily_service"].search.return_value = []
        
        result = await tavily_web_search.fn(mock_context, "test query")
        
        assert result == ""

    @pytest.mark.asyncio
    async def test_tavily_web_search_single_result(self, mock_context):
        single_result = [TavilySearchResult(
            title="Single Result",
            url="https://example.com",
            content="Single test content"
        )]
        
        mock_context.request_context.lifespan_context["tavily_service"].search.return_value = single_result
        
        result = await tavily_web_search.fn(mock_context, "test query")
        
        expected_response = str(single_result[0])
        assert result == expected_response

    @pytest.mark.asyncio
    async def test_tavily_web_search_logging(self, mock_context, sample_search_results, caplog):
        mock_context.request_context.lifespan_context["tavily_service"].search.return_value = sample_search_results
        
        with caplog.at_level(logging.INFO):
            await tavily_web_search.fn(mock_context, "test query")
        
        log_messages = [record.message for record in caplog.records]
        success_messages = [msg for msg in log_messages if "Successfully processed search request" in msg]
        assert len(success_messages) > 0
        assert "2 results" in success_messages[0]

    @pytest.mark.asyncio
    async def test_tavily_web_search_warning_logging(self, mock_context, caplog):
        mock_context.request_context.lifespan_context["tavily_service"].search.side_effect = ValueError("Empty query")
        
        with caplog.at_level(logging.WARNING):
            with pytest.raises(ToolError):
                await tavily_web_search.fn(mock_context, "")
        
        log_messages = [record.message for record in caplog.records]
        warning_messages = [msg for msg in log_messages if "Input validation error" in msg]
        assert len(warning_messages) > 0

    @pytest.mark.asyncio
    async def test_tavily_web_search_error_logging(self, mock_context, caplog):
        mock_context.request_context.lifespan_context["tavily_service"].search.side_effect = TavilyServiceError("API failure")
        
        with caplog.at_level(logging.ERROR):
            with pytest.raises(ToolError):
                await tavily_web_search.fn(mock_context, "test query")
        
        log_messages = [record.message for record in caplog.records]
        error_messages = [msg for msg in log_messages if "Tavily service error" in msg]
        assert len(error_messages) > 0


class TestIntegration:
    @pytest.mark.asyncio
    async def test_full_server_workflow(self):
        mock_server = MagicMock(spec=FastMCP)
        sample_results = [
            TavilySearchResult(
                title="Integration Test",
                url="https://example.com",
                content="Integration test content"
            )
        ]

        with patch('mcp_server_tavily.server.get_tavily_service') as mock_get_service:
            mock_tavily_service = AsyncMock(spec=_TavilyService)
            mock_tavily_service.search.return_value = sample_results
            mock_get_service.return_value = mock_tavily_service

            async with app_lifespan(mock_server) as context:
                mock_context = MagicMock(spec=Context)
                mock_context.request_context.lifespan_context = context
                
                result = await tavily_web_search.fn(mock_context, "integration test")
                
                expected_response = str(sample_results[0])
                assert result == expected_response
                
                mock_tavily_service.search.assert_called_once_with(
                    query="integration test", max_results=None
                )

    def test_server_tool_registration(self):
        """Test that the tavily_web_search tool is properly registered with the server."""
        # This test verifies that the decorator properly registers the tool
        # We can check that the tool is a FunctionTool and has the correct properties
        assert hasattr(tavily_web_search, 'fn')
        assert callable(tavily_web_search.fn)
        assert tavily_web_search.name == "tavily_web_search"
        
        # The exact implementation depends on FastMCP's internal structure
        # This is a basic check that the server exists and has been configured
        assert mcp_server.name == "tavily"