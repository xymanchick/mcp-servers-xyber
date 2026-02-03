import asyncio
import pytest
from typing import Any, Generator, Dict, List
from unittest.mock import AsyncMock, MagicMock

from qdrant_client.models import CollectionInfo, ScoredPoint

from mcp_server_qdrant.qdrant import QdrantConnector


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        yield loop
    finally:
        loop.close()


@pytest.fixture
def mock_qdrant_connector() -> AsyncMock:
    mock_connector = AsyncMock(spec=QdrantConnector)

    mock_connector.store.return_value = None

    mock_search_result = MagicMock()
    mock_search_result.points = []
    mock_connector.search.return_value = mock_search_result

    mock_collection_info = MagicMock(spec=CollectionInfo)
    mock_collection_info.status = "green"
    mock_collection_info.vectors_count = 100
    mock_collection_info.segments_count = 1
    mock_collection_info.disk_data_size = 1024
    mock_collection_info.ram_data_size = 512
    mock_collection_info.payload_schema = {"field": "keyword"}
    mock_connector.get_collection_details.return_value = mock_collection_info

    mock_connector.get_collection_names.return_value = ["test_collection", "default_collection"]

    return mock_connector


@pytest.fixture
def mock_context(mock_qdrant_connector: AsyncMock):
    from fastmcp import Context
    context = MagicMock(spec=Context)
    context.request_context.lifespan_context = {
        "qdrant_connector": mock_qdrant_connector
    }
    return context


@pytest.fixture
def sample_scored_points() -> List[ScoredPoint]:
    point1 = MagicMock(spec=ScoredPoint)
    point1.id = "point_1"
    point1.version = 1
    point1.score = 0.95
    point1.payload = {
        "content": "First test document about machine learning",
        "metadata": {
            "user": "alice",
            "category": "ai",
            "timestamp": "2023-01-01T00:00:00Z"
        }
    }
    point1.vector = None
    point1.shard_key = None

    point2 = MagicMock(spec=ScoredPoint)
    point2.id = "point_2"
    point2.version = 1
    point2.score = 0.87
    point2.payload = {
        "content": "Second test document about data science",
        "metadata": {
            "user": "bob",
            "category": "data",
            "timestamp": "2023-01-02T00:00:00Z"
        }
    }
    point2.vector = None
    point2.shard_key = None

    point3 = MagicMock(spec=ScoredPoint)
    point3.id = "point_3"
    point3.version = 1
    point3.score = 0.72
    point3.payload = {
        "content": "Third test document about natural language processing",
        "metadata": {
            "user": "alice",
            "category": "nlp",
            "timestamp": "2023-01-03T00:00:00Z"
        }
    }
    point3.vector = None
    point3.shard_key = None

    return [point1, point2, point3]


@pytest.fixture
def valid_store_request() -> Dict[str, Any]:
    return {
        "collection_name": "test_collection",
        "information": "This is comprehensive test information about machine learning algorithms and their applications in real-world scenarios.",
        "metadata": {
            "user_id": "test_user_123",
            "category": "machine_learning",
            "tags": ["ai", "ml", "algorithms"],
            "priority": "high",
            "created_at": "2023-01-01T00:00:00Z",
            "source": "research_paper"
        }
    }


@pytest.fixture
def valid_find_request() -> Dict[str, Any]:
    return {
        "collection_name": "test_collection",
        "query": "machine learning algorithms neural networks",
        "search_limit": 10,
        "filters": {
            "user_id": "test_user_123",
            "category": "machine_learning"
        }
    }


@pytest.fixture
def valid_collection_info_request() -> Dict[str, Any]:
    return {
        "collection_name": "test_collection"
    }


@pytest.fixture
def sample_collection_info() -> CollectionInfo:
    mock_info = MagicMock(spec=CollectionInfo)
    mock_info.status = "green"
    mock_info.vectors_count = 1500
    mock_info.segments_count = 3
    mock_info.disk_data_size = 2048576  # ~2MB
    mock_info.ram_data_size = 1048576   # ~1MB
    mock_info.payload_schema = {
        "user_id": "keyword",
        "category": "keyword",
        "tags": "keyword",
        "priority": "keyword",
        "created_at": "keyword"
    }
    return mock_info


@pytest.fixture
def invalid_requests() -> Dict[str, Dict[str, Any]]:
    return {
        "store_missing_collection": {
            "information": "Test information"
            # Missing required collection_name
        },
        "store_wrong_type_collection": {
            "collection_name": 123,  # Should be string
            "information": "Test information"
        },
        "store_missing_information": {
            "collection_name": "test_collection"
            # Missing required information
        },
        "find_missing_query": {
            "collection_name": "test_collection"
            # Missing required query
        },
        "find_invalid_limit": {
            "collection_name": "test_collection",
            "query": "test",
            "search_limit": "not_a_number"  # Should be integer
        },
        "collection_info_missing_name": {
            # Missing required collection_name
        },
        "collection_info_wrong_type": {
            "collection_name": ["not", "a", "string"]  # Should be string
        }
    }
