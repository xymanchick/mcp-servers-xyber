import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_server_qdrant.qdrant.config import (
    CollectionConfig,
    HnswConfig,
    PayloadIndexConfig,
    PayloadIndexType,
    QdrantConfig,
)
from mcp_server_qdrant.qdrant.embeddings.base import EmbeddingProvider
from mcp_server_qdrant.qdrant.module import QdrantConnector


class MockEmbeddingProvider(EmbeddingProvider):
    def __init__(self, vector_size: int = 384, vector_name: str = "text"):
        self.vector_size = vector_size
        self.vector_name = vector_name

    async def embed_documents(self, documents: list[str]) -> list[list[float]]:
        return [[0.1] * self.vector_size for _ in documents]

    async def embed_query(self, query: str) -> list[float]:
        return [0.2] * self.vector_size

    def get_vector_name(self) -> str:
        return self.vector_name

    def get_vector_size(self) -> int:
        return self.vector_size


@pytest.fixture(autouse=True)
def disable_all_logging():
    logging.disable(logging.ERROR)
    yield
    logging.disable(logging.NOTSET)


@pytest.fixture(autouse=True)
def clear_dependency_container():
    """Clear the DependencyContainer between tests."""
    from mcp_server_qdrant.dependencies import DependencyContainer

    DependencyContainer._qdrant_connector = None
    yield
    DependencyContainer._qdrant_connector = None


@pytest.fixture
def mock_logger():
    with patch("mcp_server_qdrant.qdrant.module.logger") as mock_log:
        yield mock_log


@pytest.fixture
def mock_uuid():
    with patch("uuid.uuid4") as mock_uuid_func:
        mock_uuid_func.return_value.hex = "test-uuid-12345"
        yield mock_uuid_func


@pytest.fixture
def sample_embeddings():
    return {
        "document_embeddings": [[0.1, 0.2, 0.3, 0.4] * 96],  # 384 dimensions
        "query_embedding": [0.2, 0.3, 0.4, 0.5] * 96,  # 384 dimensions
        "vector_size": 384,
        "vector_name": "text",
    }


@pytest.fixture
def sample_entries():
    from mcp_server_qdrant.qdrant.module import Entry

    return [
        Entry(
            content="Python is a high-level programming language",
            metadata={
                "category": "programming",
                "user_id": "alice",
                "difficulty": "beginner",
            },
        ),
        Entry(
            content="Machine learning algorithms for data science",
            metadata={
                "category": "data_science",
                "user_id": "bob",
                "difficulty": "advanced",
            },
        ),
        Entry(
            content="Web development with FastAPI framework",
            metadata={
                "category": "web_dev",
                "user_id": "alice",
                "difficulty": "intermediate",
            },
        ),
        Entry(
            content="Database design and optimization techniques",
            metadata={
                "category": "database",
                "user_id": "charlie",
                "difficulty": "advanced",
            },
        ),
    ]


@pytest.fixture
def simple_entries():
    from mcp_server_qdrant.qdrant.module import Entry

    return [
        Entry(content="Hello world"),
        Entry(content="Test document", metadata={"type": "test"}),
        Entry(content="Sample text", metadata={"category": "sample"}),
    ]


@pytest.fixture
def complex_entries():
    from mcp_server_qdrant.qdrant.module import Entry

    return [
        Entry(
            content="Advanced machine learning techniques in natural language processing",
            metadata={
                "category": "research",
                "subcategory": "ml",
                "author": "Dr. Smith",
                "year": 2024,
                "tags": ["nlp", "deep-learning", "transformers"],
                "difficulty": "advanced",
                "language": "en",
            },
        ),
        Entry(
            content="Introduction to Python programming for beginners",
            metadata={
                "category": "tutorial",
                "subcategory": "programming",
                "author": "Jane Doe",
                "year": 2023,
                "tags": ["python", "basics", "programming"],
                "difficulty": "beginner",
                "language": "en",
            },
        ),
    ]


@pytest.fixture
def multilingual_entries():
    from mcp_server_qdrant.qdrant.module import Entry

    return [
        Entry(content="Hello, world!", metadata={"language": "en", "has_emoji": True}),
        Entry(content="Privet, mir!", metadata={"language": "ru", "has_emoji": True}),
        Entry(content="Hola, mundo!", metadata={"language": "es", "has_emoji": True}),
        Entry(
            content="Konnichiwa, sekai!", metadata={"language": "ja", "has_emoji": True}
        ),
    ]


@pytest.fixture
def sample_search_results():
    mock_results = MagicMock()
    mock_results.points = [
        MagicMock(
            id="1",
            score=0.95,
            payload={
                "document": "Python programming tutorial",
                "metadata": {"category": "programming", "user_id": "alice"},
            },
            vector=None,
        ),
        MagicMock(
            id="2",
            score=0.87,
            payload={
                "document": "Advanced Python concepts",
                "metadata": {"category": "programming", "user_id": "bob"},
            },
            vector=None,
        ),
        MagicMock(
            id="3",
            score=0.75,
            payload={
                "document": "Python web frameworks",
                "metadata": {"category": "web_dev", "user_id": "alice"},
            },
            vector=None,
        ),
    ]
    return mock_results


@pytest.fixture
def collection_info_sample():
    mock_info = MagicMock()
    mock_info.status = "green"
    mock_info.points_count = 1000
    mock_info.vectors_count = 1000
    mock_info.segments_count = 2
    return mock_info


@pytest.fixture
def mock_client_with_errors():
    mock_client = AsyncMock()

    mock_client.collection_exists.side_effect = Exception("Connection error")
    mock_client.get_collections.side_effect = Exception("API error")
    mock_client.create_collection.side_effect = Exception("Creation failed")
    mock_client.upsert.side_effect = Exception("Upsert failed")
    mock_client.query_points.side_effect = Exception("Query failed")

    return mock_client


@pytest.fixture
def mock_client_collection_not_found():
    mock_client = AsyncMock()

    mock_client.collection_exists.return_value = False
    mock_client.get_collection.side_effect = Exception("Collection not found")
    mock_client.get_collections.return_value = MagicMock(collections=[])

    return mock_client


@pytest.fixture
def performance_test_data():
    from mcp_server_qdrant.qdrant.module import Entry

    entries = []
    for i in range(100):
        entries.append(
            Entry(
                content=f"Performance test document {i}. "
                + "Lorem ipsum dolor sit amet. " * 10,
                metadata={
                    "doc_id": i,
                    "batch": i // 10,
                    "category": f"category_{i % 5}",
                    "size": "large",
                },
            )
        )

    return entries


@pytest.fixture
def config_with_custom_distance():
    return {
        "qdrant_url": "http://localhost:6333",
        "collection_name": "test_collection",
        "distance": "Cosine",
        "vector_size": 128,
        "embedding_provider": "openai",
        "openai_api_key": "test-key",
    }


@pytest.fixture
def config_minimal():
    return {
        "qdrant_url": "http://localhost:6333",
        "collection_name": "minimal_test",
        "embedding_provider": "openai",
        "openai_api_key": "test-key",
    }


@pytest.fixture
def config_with_auth():
    """Configuration with authentication."""
    return {
        "qdrant_url": "http://localhost:6333",
        "collection_name": "auth_test",
        "qdrant_api_key": "secret-api-key",
        "embedding_provider": "openai",
        "openai_api_key": "test-key",
    }


@pytest.fixture
def config_remote_cluster():
    """Configuration for remote Qdrant cluster."""
    return {
        "qdrant_url": "https://xyz-example.us-east-1-0.aws.cloud.qdrant.io:6333",
        "collection_name": "remote_test",
        "qdrant_api_key": "cluster-api-key",
        "embedding_provider": "openai",
        "openai_api_key": "test-key",
        "vector_size": 1536,
    }


@pytest.fixture
def mock_async_qdrant_client():
    """Create a fully mocked AsyncQdrantClient."""
    with patch(
        "mcp_server_qdrant.qdrant.module.AsyncQdrantClient"
    ) as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        # Default mock behaviors
        mock_client.get_collections.return_value = MagicMock(collections=[])
        mock_client.collection_exists.return_value = True
        mock_client.create_collection.return_value = None
        mock_client.create_payload_index.return_value = None
        mock_client.upsert.return_value = None
        mock_client.query_points.return_value = MagicMock(points=[])

        yield mock_client


@pytest.fixture
def mock_config():
    config = QdrantConfig()
    config.host = "localhost"
    config.port = 6333
    config.api_key = "test-key"
    config.local_path = None
    config.collection_config = CollectionConfig(
        hnsw_config=HnswConfig(
            m=0, ef_construct=200, payload_m=16
        ),  # m=0 for tenant setup
        payload_indexes=[
            PayloadIndexConfig(
                field_name="metadata.user_id",
                index_type=PayloadIndexType.KEYWORD,
                is_tenant=True,
            ),
            PayloadIndexConfig(
                field_name="metadata.category", index_type=PayloadIndexType.KEYWORD
            ),
        ],
    )
    return config


@pytest.fixture
def mock_config_non_tenant():
    config = QdrantConfig()
    config.host = "localhost"
    config.port = 6333
    config.api_key = "test-key"
    config.local_path = None
    config.collection_config = CollectionConfig(
        hnsw_config=HnswConfig(m=16, ef_construct=200),  # Normal HNSW config
        payload_indexes=[
            PayloadIndexConfig(
                field_name="metadata.category", index_type=PayloadIndexType.KEYWORD
            ),
            PayloadIndexConfig(
                field_name="metadata.score", index_type=PayloadIndexType.FLOAT
            ),
        ],
    )
    return config


@pytest.fixture
def mock_config_local():
    config = QdrantConfig()
    config.host = ""
    config.port = 6333
    config.api_key = None
    config.local_path = "/tmp/qdrant_test"
    config.collection_config = CollectionConfig(
        hnsw_config=HnswConfig(m=16, ef_construct=100), payload_indexes=[]
    )
    return config


@pytest.fixture
def mock_embedding_provider():
    return MockEmbeddingProvider()


@pytest.fixture
def mock_embedding_provider_large():
    return MockEmbeddingProvider(vector_size=1536, vector_name="large_embeddings")


@pytest.fixture
def mock_embedding_provider_small():
    return MockEmbeddingProvider(vector_size=128, vector_name="small_embeddings")


@pytest.fixture
def qdrant_connector(mock_config, mock_embedding_provider):
    with patch(
        "mcp_server_qdrant.qdrant.module.AsyncQdrantClient"
    ) as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        connector = QdrantConnector(mock_config, mock_embedding_provider)
        connector._client = mock_client
        return connector
