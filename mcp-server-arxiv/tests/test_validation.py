from unittest.mock import Mock, PropertyMock, patch

import pytest
import requests
from arxiv import Result
from fastmcp import Context
from fastmcp.exceptions import ToolError

from mcp_server_arxiv import get_arxiv_service
from mcp_server_arxiv.server import arxiv_search


def mock_response(status_code, content):
    response = requests.Response()
    response.status_code = status_code
    response._content = content.encode()
    return response


@pytest.fixture
def mock_context() -> Context:
    """Fixture to create a mock Context for direct tool calls."""
    class MockRequestContext:
        def __init__(self, lifespan_ctx):
            self.lifespan_context = lifespan_ctx

    mock_lifespan_context = {'arxiv_service': get_arxiv_service()}
    ctx = Context(fastmcp=Mock())
    ctx.fastmcp._mcp_server.request_context = MockRequestContext(mock_lifespan_context)
    return ctx


@pytest.mark.asyncio
async def test_query_empty_string(mock_context):
    with pytest.raises(ToolError, match="Input validation error: Search query cannot be empty."):
        await arxiv_search.fn(ctx=mock_context, query="", max_results=5)


@pytest.mark.asyncio
async def test_query_integer(mock_context):
    with pytest.raises(ToolError, match="An unexpected error occurred during search."):
        await arxiv_search.fn(ctx=mock_context, query=3, max_results=5)


@pytest.mark.asyncio
async def test_query_valid_but_arxive_failed(mock_context):
    with pytest.raises(ToolError, match="An unexpected error occurred during search."):
        with patch('requests.Session.request', side_effect=mock_response(200, '')):
            await arxiv_search.fn(ctx=mock_context, query='a' * 1000, max_results=5)


@pytest.mark.asyncio
async def test_query_empty_results(mock_context):
    with patch('arxiv.Client.results', return_value=iter(())):
        result = await arxiv_search.fn(ctx=mock_context, query='a' * 1000, max_results=5)
    assert result == "No relevant papers found or processed on arXiv for the given query"


@pytest.mark.asyncio
async def test_query_dump_does_not_exists(mock_context):
    results = [Result(
        '1234.56789',
        title='mock paper',
        authors=[Result.Author('Author A')],
        summary='A mock summary.',
        links=[Result.Link('http://example.com/mock.pdf', title='pdf')],
    )]
    with patch('arxiv.Client.results', return_value=iter(results)):
        with patch('requests.Session.request', side_effect=mock_response(404, '')):
            result = await arxiv_search.fn(ctx=mock_context, query='a' * 1000, max_results=5)

    assert "Processing Error: [Unexpected error processing PDF 1234.56789: HTTPError - HTTP Error 404: Not Found]" in result
