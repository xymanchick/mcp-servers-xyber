from contextlib import nullcontext as not_rise_error
from unittest.mock import AsyncMock, patch

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError
from mcp.types import TextContent
from pytest import raises
from qdrant_client.http.models.models import QueryResponse


@pytest.mark.asyncio
@pytest.mark.parametrize(
        ["error", "request_data", "expected"],
        [
            (
                    not_rise_error(),
                    dict(
                        information="1",
                        collection_name="test_collection",
                    ),
                [TextContent(type='text', text="Remembered: 1 in collection test_collection", annotations=None)]
            ),
            (
                    raises(
                        ToolError,
                        match="Invalid parameters: collection_name: Field required; information: Field required",
                    ),
                    dict(metadata={"source": "test_source", "tenant": "test_tenant"}),
                None
            ),
            (
                    raises(ToolError, match="Invalid parameters: information: Input should be a valid string"),
                    dict(
                        information=1,
                        collection_name="test_collection",
                    ),
                None
            ),
        ],
        ids=["valid", "missed_required_fields", "validation_error"]
    )
@patch('mcp_server_qdrant.qdrant.module.QdrantConnector.store', new_callable=AsyncMock)
async def test_qdrant_store(_, mcp_server, error, request_data: dict, expected: str | None):
    """Validation test for `qdrant_store` tool."""

    with error:
        async with Client(mcp_server) as client:
            result = await client.call_tool("qdrant_store", {"request": request_data})

            assert result == expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
        ["error", "request_data", "expected"],
        [
            (
                    not_rise_error(),
                    dict(
                        query="query",
                        collection_name="test_collection",
                        search_limit=1,
                        filters={"key": "value"},
                    ),
                    (QueryResponse(points=[]), [])
            ),
            (
                    not_rise_error(),
                    dict(
                        query="query",
                        collection_name="test_collection",
                        search_limit=1,
                        filters={"key": "value"},
                    ),
                    (
                        None,
                        [TextContent(type='text', text="No information found for the query 'query'", annotations=None)]
                    )
            ),
            (
                    raises(ToolError,match="Invalid parameters: collection_name: Field required"),
                    dict(
                        query="query",
                        search_limit=1,
                        filters={"key": "value"},
                    ),
                    (None, None)
            ),
            (
                    raises(ToolError, match="Invalid parameters: search_limit: Input should be a valid integer"),
                    dict(
                        query="query",
                        collection_name="test_collection",
                        search_limit="limit",
                    ),
                    (None, None)
            ),
        ],
        ids=["valid", "valid_without_points", "missed_required_fields", "validation_error"]
    )
@patch('mcp_server_qdrant.qdrant.module.QdrantConnector.search', new_callable=AsyncMock)
async def test_qdrant_find(mock_search, mcp_server, error, request_data: dict, expected: tuple):
    """Validation test for `qdrant_find` tool."""

    query_response, expected_response = expected
    mock_search.return_value = query_response

    with error:
        async with Client(mcp_server) as client:
            result = await client.call_tool("qdrant_find", {"request": request_data})

            assert result == expected_response


@pytest.mark.asyncio
@pytest.mark.parametrize(
        ["error", "request_data"],
        [
            (not_rise_error(), dict(collection_name="test_collection")),
            (raises(ToolError, match="Invalid parameters: collection_name: Field required"), dict()),
            (
                    raises(ToolError, match="Invalid parameters: collection_name: Input should be a valid string"),
                    dict(collection_name=1),
            ),
        ],
        ids=["valid", "missed_required_fields", "validation_error"]
    )
@patch('mcp_server_qdrant.qdrant.module.QdrantConnector.get_collection_details', new_callable=AsyncMock)
async def test_get_collection_info(_, mcp_server, error, request_data: dict):
    """Validation test for `get_collection_info` tool."""

    with error:
        async with Client(mcp_server) as client:
            await client.call_tool("qdrant_get_collection_info", {"request": request_data})
