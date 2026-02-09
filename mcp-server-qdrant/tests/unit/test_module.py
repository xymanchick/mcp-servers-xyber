import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch, call
from typing import Any

from qdrant_client import models
from qdrant_client.models import CollectionInfo, QueryResponse
from pydantic import ValidationError

from mcp_server_qdrant.qdrant.module import QdrantConnector, Entry
from mcp_server_qdrant.qdrant.config import (
    QdrantConfig,
    QdrantAPIError,
    PayloadIndexConfig,
    PayloadIndexType,
    HnswConfig,
    CollectionConfig,
    EmbeddingProviderSettings
)
from mcp_server_qdrant.qdrant.embeddings.base import EmbeddingProvider


class TestEntry:
    def test_entry_creation_with_content_only(self):
        entry = Entry(content="Test content")
        assert entry.content == "Test content"
        assert entry.metadata is None

    def test_entry_creation_with_metadata(self):
        metadata = {"user_id": "alice", "category": "work"}
        entry = Entry(content="Test content", metadata=metadata)
        assert entry.content == "Test content"
        assert entry.metadata == metadata

    def test_entry_string_representation(self):
        metadata = {"user_id": "alice"}
        entry = Entry(content="Test content", metadata=metadata)
        expected = "Entry(content=Test content, metadata={'user_id': 'alice'})"
        assert str(entry) == expected


class TestQdrantConnector:
    def test_initialization(self, mock_config, mock_embedding_provider):
        with patch('mcp_server_qdrant.qdrant.module.AsyncQdrantClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            connector = QdrantConnector(mock_config, mock_embedding_provider)

            assert connector._config == mock_config
            assert connector._embedding_provider == mock_embedding_provider
            mock_client_class.assert_called_once_with(
                location=mock_config.location,
                api_key=mock_config.api_key,
                path=mock_config.local_path
            )

    @pytest.mark.asyncio
    async def test_get_collection_names_success(self, qdrant_connector):
        mock_collections = [
            MagicMock(name="collection1"),
            MagicMock(name="collection2"),
            MagicMock(name="collection3")
        ]
        mock_collections[0].name = "collection1"
        mock_collections[1].name = "collection2"
        mock_collections[2].name = "collection3"

        mock_response = MagicMock(collections=mock_collections)
        qdrant_connector._client.get_collections.return_value = mock_response

        result = await qdrant_connector.get_collection_names()

        assert result == ["collection1", "collection2", "collection3"]
        qdrant_connector._client.get_collections.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_collection_names_empty(self, qdrant_connector):
        mock_response = MagicMock(collections=[])
        qdrant_connector._client.get_collections.return_value = mock_response

        result = await qdrant_connector.get_collection_names()

        assert result == []
        qdrant_connector._client.get_collections.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_collection_details_success(self, qdrant_connector):
        collection_name = "test_collection"
        mock_info = MagicMock()
        mock_info.status = "green"
        mock_info.points_count = 1000

        qdrant_connector._client.get_collection.return_value = mock_info

        result = await qdrant_connector.get_collection_details(collection_name)

        assert result == mock_info
        qdrant_connector._client.get_collection.assert_called_once_with(
            collection_name=collection_name
        )

    @pytest.mark.asyncio
    async def test_get_collection_details_not_found(self, qdrant_connector):
        collection_name = "nonexistent_collection"
        qdrant_connector._client.get_collection.side_effect = Exception("not found")

        with pytest.raises(QdrantAPIError) as exc_info:
            await qdrant_connector.get_collection_details(collection_name)

        assert "not found" in str(exc_info.value)
        qdrant_connector._client.get_collection.assert_called_once_with(
            collection_name=collection_name
        )

    @pytest.mark.asyncio
    async def test_get_collection_details_api_error(self, qdrant_connector):
        collection_name = "test_collection"
        qdrant_connector._client.get_collection.side_effect = Exception("Server error")

        with pytest.raises(QdrantAPIError) as exc_info:
            await qdrant_connector.get_collection_details(collection_name)

        assert "Failed to get details" in str(exc_info.value)
        assert "Server error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_store_success_new_collection(self, qdrant_connector):
        entry = Entry(content="Test document", metadata={"user_id": "alice"})
        collection_name = "test_collection"

        qdrant_connector._client.collection_exists = AsyncMock(return_value=False)
        qdrant_connector._ensure_collection_exists = AsyncMock()
        qdrant_connector._client.upsert = AsyncMock()

        with patch('uuid.uuid4') as mock_uuid:
            mock_uuid.return_value.hex = "test-uuid"

            await qdrant_connector.store(entry, collection_name)

        qdrant_connector._ensure_collection_exists.assert_called_once_with(collection_name)

        qdrant_connector._client.upsert.assert_called_once()
        call_args = qdrant_connector._client.upsert.call_args

        assert call_args[1]['collection_name'] == collection_name
        points = call_args[1]['points']
        assert len(points) == 1

        point = points[0]
        assert point.id == "test-uuid"
        assert point.payload == {
            "document": "Test document",
            "metadata": {"user_id": "alice"}
        }
        assert point.vector == {"text": [0.1] * 384}  # From mock embedding

    @pytest.mark.asyncio
    async def test_store_existing_collection(self, qdrant_connector):
        entry = Entry(content="Test document")
        collection_name = "existing_collection"

        qdrant_connector._ensure_collection_exists = AsyncMock()
        qdrant_connector._client.upsert = AsyncMock()

        await qdrant_connector.store(entry, collection_name)

        qdrant_connector._ensure_collection_exists.assert_called_once_with(collection_name)
        qdrant_connector._client.upsert.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_embedding_error(self, qdrant_connector):
        entry = Entry(content="Test document")
        collection_name = "test_collection"

        qdrant_connector._embedding_provider.embed_documents = AsyncMock(
            side_effect=Exception("Embedding failed")
        )
        qdrant_connector._ensure_collection_exists = AsyncMock()

        with pytest.raises(QdrantAPIError) as exc_info:
            await qdrant_connector.store(entry, collection_name)

        assert "Failed to store entry" in str(exc_info.value)
        assert "Embedding failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_store_upsert_error(self, qdrant_connector):
        entry = Entry(content="Test document")
        collection_name = "test_collection"

        qdrant_connector._ensure_collection_exists = AsyncMock()
        qdrant_connector._client.upsert = AsyncMock(side_effect=Exception("Upsert failed"))

        with pytest.raises(QdrantAPIError) as exc_info:
            await qdrant_connector.store(entry, collection_name)

        assert "Failed to store entry" in str(exc_info.value)
        assert "Upsert failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_search_success_no_filters(self, qdrant_connector):
        query = "test query"
        collection_name = "test_collection"

        qdrant_connector._client.collection_exists = AsyncMock(return_value=True)

        mock_results = MagicMock()
        mock_results.points = [
            MagicMock(
                id="1",
                score=0.95,
                payload={"document": "Test doc 1", "metadata": {"user_id": "alice"}},
                vector=None
            ),
            MagicMock(
                id="2",
                score=0.85,
                payload={"document": "Test doc 2", "metadata": {"user_id": "bob"}},
                vector=None
            )
        ]
        qdrant_connector._client.query_points = AsyncMock(return_value=mock_results)

        result = await qdrant_connector.search(query, collection_name, limit=10)

        assert result == mock_results
        qdrant_connector._client.collection_exists.assert_called_once_with(collection_name)
        qdrant_connector._client.query_points.assert_called_once_with(
            collection_name=collection_name,
            query=[0.2] * 384,  # From mock embedding
            query_filter=None,
            limit=10,
            using="text",
            with_payload=True,
            with_vectors=False
        )

    @pytest.mark.asyncio
    async def test_search_success_with_filters(self, qdrant_connector):
        query = "test query"
        collection_name = "test_collection"
        filters = {"metadata.user_id": "alice", "metadata.category": "work"}

        qdrant_connector._client.collection_exists = AsyncMock(return_value=True)
        mock_results = MagicMock()
        mock_results.points = []
        qdrant_connector._client.query_points = AsyncMock(return_value=mock_results)

        await qdrant_connector.search(query, collection_name, filters=filters)

        call_args = qdrant_connector._client.query_points.call_args[1]
        query_filter = call_args['query_filter']

        assert query_filter is not None
        assert len(query_filter.must) == 2

        conditions = query_filter.must
        field_keys = [cond.key for cond in conditions]
        field_values = [cond.match.value for cond in conditions]

        assert "metadata.user_id" in field_keys
        assert "metadata.category" in field_keys
        assert "alice" in field_values
        assert "work" in field_values

    @pytest.mark.asyncio
    async def test_search_collection_not_exists(self, qdrant_connector):
        query = "test query"
        collection_name = "nonexistent_collection"

        qdrant_connector._client.collection_exists = AsyncMock(return_value=False)
        qdrant_connector.get_collection_names = AsyncMock(return_value=["other_collection"])

        with pytest.raises(QdrantAPIError) as exc_info:
            await qdrant_connector.search(query, collection_name)

        assert "does not exist" in str(exc_info.value)
        assert "other_collection" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_search_embedding_error(self, qdrant_connector):
        query = "test query"
        collection_name = "test_collection"

        qdrant_connector._client.collection_exists = AsyncMock(return_value=True)
        qdrant_connector._embedding_provider.embed_query = AsyncMock(
            side_effect=Exception("Embedding error")
        )

        with pytest.raises(QdrantAPIError) as exc_info:
            await qdrant_connector.search(query, collection_name)

        assert "Failed to search" in str(exc_info.value)
        assert "Embedding error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_search_api_error(self, qdrant_connector):
        query = "test query"
        collection_name = "test_collection"

        qdrant_connector._client.collection_exists = AsyncMock(return_value=True)
        qdrant_connector._client.query_points = AsyncMock(
            side_effect=Exception("API error")
        )

        with pytest.raises(QdrantAPIError) as exc_info:
            await qdrant_connector.search(query, collection_name)

        assert "Failed to search" in str(exc_info.value)
        assert "API error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_search_custom_parameters(self, qdrant_connector):
        query = "test query"
        collection_name = "test_collection"

        qdrant_connector._client.collection_exists = AsyncMock(return_value=True)
        mock_results = MagicMock()
        mock_results.points = []
        qdrant_connector._client.query_points = AsyncMock(return_value=mock_results)

        await qdrant_connector.search(
            query=query,
            collection_name=collection_name,
            limit=5,
            with_payload=["document"],
            with_vectors=True
        )

        call_args = qdrant_connector._client.query_points.call_args[1]
        assert call_args['limit'] == 5
        assert call_args['with_payload'] == ["document"]
        assert call_args['with_vectors'] is True

    @pytest.mark.asyncio
    async def test_ensure_collection_exists_new_collection(self, qdrant_connector):
        collection_name = "new_collection"

        qdrant_connector._client.collection_exists = AsyncMock(return_value=False)
        qdrant_connector._create_configured_collection = AsyncMock()

        await qdrant_connector._ensure_collection_exists(collection_name)

        qdrant_connector._client.collection_exists.assert_called_once_with(collection_name)
        qdrant_connector._create_configured_collection.assert_called_once_with(collection_name)

    @pytest.mark.asyncio
    async def test_ensure_collection_exists_existing_collection(self, qdrant_connector):
        collection_name = "existing_collection"

        qdrant_connector._client.collection_exists = AsyncMock(return_value=True)
        qdrant_connector._ensure_payload_indexes = AsyncMock()

        await qdrant_connector._ensure_collection_exists(collection_name)

        qdrant_connector._client.collection_exists.assert_called_once_with(collection_name)
        qdrant_connector._ensure_payload_indexes.assert_called_once_with(collection_name)

    @pytest.mark.asyncio
    async def test_create_configured_collection_success(self, qdrant_connector):
        collection_name = "test_collection"

        qdrant_connector._client.create_collection = AsyncMock()
        qdrant_connector._ensure_payload_indexes = AsyncMock()

        await qdrant_connector._create_configured_collection(collection_name)

        call_args = qdrant_connector._client.create_collection.call_args[1]

        assert call_args['collection_name'] == collection_name
        assert 'text' in call_args['vectors_config']

        vector_config = call_args['vectors_config']['text']
        assert vector_config.size == 384  # From mock embedding provider
        assert vector_config.distance == models.Distance.COSINE

        hnsw_config = call_args['hnsw_config']
        assert hnsw_config.m == 0  # Updated to match fixture
        assert hnsw_config.ef_construct == 200

        qdrant_connector._ensure_payload_indexes.assert_called_once_with(collection_name)

    @pytest.mark.asyncio
    async def test_create_configured_collection_error(self, qdrant_connector):
        collection_name = "test_collection"

        qdrant_connector._client.create_collection = AsyncMock(
            side_effect=Exception("Creation failed")
        )

        with pytest.raises(QdrantAPIError) as exc_info:
            await qdrant_connector._create_configured_collection(collection_name)

        assert "Failed to create collection" in str(exc_info.value)
        assert "Creation failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_ensure_payload_indexes(self, qdrant_connector):
        collection_name = "test_collection"

        qdrant_connector._create_payload_index = AsyncMock()

        await qdrant_connector._ensure_payload_indexes(collection_name)

        expected_calls = [
            call(collection_name, qdrant_connector._config.collection_config.payload_indexes[0]),
            call(collection_name, qdrant_connector._config.collection_config.payload_indexes[1])
        ]
        qdrant_connector._create_payload_index.assert_has_calls(expected_calls)

    @pytest.mark.asyncio
    async def test_create_payload_index_keyword_tenant(self, qdrant_connector):
        collection_name = "test_collection"
        index_config = PayloadIndexConfig(
            field_name="metadata.tenant_id",
            index_type=PayloadIndexType.KEYWORD,
            is_tenant=True
        )

        qdrant_connector._client.create_payload_index = AsyncMock()

        await qdrant_connector._create_payload_index(collection_name, index_config)

        call_args = qdrant_connector._client.create_payload_index.call_args[1]

        assert call_args['collection_name'] == collection_name
        assert call_args['field_name'] == "metadata.tenant_id"
        assert isinstance(call_args['field_schema'], models.KeywordIndexParams)
        assert call_args['field_schema'].is_tenant is True
        assert call_args['wait'] is True

    @pytest.mark.asyncio
    async def test_create_payload_index_regular_types(self, qdrant_connector):
        collection_name = "test_collection"

        test_cases = [
            (PayloadIndexType.INTEGER, models.PayloadSchemaType.INTEGER),
            (PayloadIndexType.FLOAT, models.PayloadSchemaType.FLOAT),
            (PayloadIndexType.TEXT, models.PayloadSchemaType.TEXT),
            (PayloadIndexType.BOOL, models.PayloadSchemaType.BOOL),
            (PayloadIndexType.GEO, models.PayloadSchemaType.GEO),
            (PayloadIndexType.DATETIME, models.PayloadSchemaType.DATETIME),
        ]

        qdrant_connector._client.create_payload_index = AsyncMock()

        for index_type, expected_schema_type in test_cases:
            index_config = PayloadIndexConfig(
                field_name=f"metadata.{index_type.value}_field",
                index_type=index_type
            )

            await qdrant_connector._create_payload_index(collection_name, index_config)

            call_args = qdrant_connector._client.create_payload_index.call_args[1]
            assert call_args['field_schema'] == expected_schema_type

    @pytest.mark.asyncio
    async def test_create_payload_index_error(self, qdrant_connector):
        collection_name = "test_collection"
        index_config = PayloadIndexConfig(
            field_name="metadata.test_field",
            index_type=PayloadIndexType.KEYWORD
        )

        qdrant_connector._client.create_payload_index = AsyncMock(
            side_effect=Exception("Index creation failed")
        )

        with pytest.raises(QdrantAPIError) as exc_info:
            await qdrant_connector._create_payload_index(collection_name, index_config)

        assert "Failed to create payload index" in str(exc_info.value)
        assert "Index creation failed" in str(exc_info.value)


class TestIntegration:
    @pytest.mark.asyncio
    async def test_full_workflow_store_and_search(self, qdrant_connector):
        collection_name = "integration_test"

        qdrant_connector._client.collection_exists = AsyncMock(side_effect=[False, True, True])
        qdrant_connector._client.create_collection = AsyncMock()
        qdrant_connector._client.create_payload_index = AsyncMock()
        qdrant_connector._client.upsert = AsyncMock()

        entries = [
            Entry(content="Python programming tutorial", metadata={"category": "programming", "user_id": "alice"}),
            Entry(content="Machine learning basics", metadata={"category": "ml", "user_id": "bob"}),
            Entry(content="Advanced Python concepts", metadata={"category": "programming", "user_id": "alice"})
        ]

        for entry in entries:
            await qdrant_connector.store(entry, collection_name)

        qdrant_connector._client.create_collection.assert_called_once()

        assert qdrant_connector._client.upsert.call_count == 3

        qdrant_connector._client.collection_exists = AsyncMock(return_value=True)
        mock_search_results = MagicMock()
        mock_search_results.points = [
            MagicMock(
                id="1",
                score=0.95,
                payload={"document": "Python programming tutorial", "metadata": {"category": "programming"}},
                vector=None
            )
        ]
        qdrant_connector._client.query_points = AsyncMock(return_value=mock_search_results)

        search_results = await qdrant_connector.search(
            "Python programming",
            collection_name,
            filters={"metadata.category": "programming"}
        )

        assert len(search_results.points) == 1
        assert "Python programming tutorial" in search_results.points[0].payload["document"]

    @pytest.mark.asyncio
    async def test_error_propagation_chain(self, qdrant_connector):
        collection_name = "error_test"

        qdrant_connector._client.collection_exists = AsyncMock(
            side_effect=Exception("Connection failed")
        )

        entry = Entry(content="Test content")

        with pytest.raises(QdrantAPIError) as exc_info:
            await qdrant_connector.store(entry, collection_name)

        assert "Failed to store entry" in str(exc_info.value)
        assert "Connection failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_batch_operations_performance(self, qdrant_connector):
        collection_name = "batch_test"

        qdrant_connector._client.collection_exists = AsyncMock(return_value=True)
        qdrant_connector._ensure_payload_indexes = AsyncMock()
        qdrant_connector._client.upsert = AsyncMock()

        entries = [Entry(content=f"Document {i}") for i in range(10)]

        for entry in entries:
            await qdrant_connector.store(entry, collection_name)

        assert qdrant_connector._client.upsert.call_count == 10

        assert qdrant_connector._ensure_payload_indexes.call_count == 10

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, qdrant_connector):
        import asyncio

        collection_name = "concurrent_test"

        qdrant_connector._client.collection_exists = AsyncMock(return_value=True)
        qdrant_connector._ensure_payload_indexes = AsyncMock()
        qdrant_connector._client.upsert = AsyncMock()
        qdrant_connector._client.query_points = AsyncMock(
            return_value=MagicMock(points=[])
        )

        async def store_operation(i):
            entry = Entry(content=f"Concurrent document {i}")
            await qdrant_connector.store(entry, collection_name)

        async def search_operation(i):
            await qdrant_connector.search(f"query {i}", collection_name)

        tasks = []
        for i in range(5):
            tasks.append(store_operation(i))
            tasks.append(search_operation(i))

        await asyncio.gather(*tasks)

        assert qdrant_connector._client.upsert.call_count == 5
        assert qdrant_connector._client.query_points.call_count == 5


class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_empty_query_search(self, qdrant_connector):
        qdrant_connector._client.collection_exists = AsyncMock(return_value=True)
        qdrant_connector._client.query_points = AsyncMock(
            return_value=MagicMock(points=[])
        )

        result = await qdrant_connector.search("", "test_collection")

        assert len(result.points) == 0
        qdrant_connector._client.query_points.assert_called_once()

    @pytest.mark.asyncio
    async def test_very_long_content(self, qdrant_connector):
        long_content = "This is a very long document. " * 1000  # 30,000 chars
        entry = Entry(content=long_content)

        qdrant_connector._ensure_collection_exists = AsyncMock()
        qdrant_connector._client.upsert = AsyncMock()

        await qdrant_connector.store(entry, "test_collection")

        call_args = qdrant_connector._client.upsert.call_args[1]
        stored_content = call_args['points'][0].payload['document']
        assert stored_content == long_content

    @pytest.mark.asyncio
    async def test_special_characters_in_metadata(self, qdrant_connector):
        special_metadata = {
            "unicode_field": "cafe munchen star",
            "special_chars": "!@#$%^&*()_+-={}[]|\\:;\"'<>?,./"
        }
        entry = Entry(content="Test content", metadata=special_metadata)

        qdrant_connector._ensure_collection_exists = AsyncMock()
        qdrant_connector._client.upsert = AsyncMock()

        await qdrant_connector.store(entry, "test_collection")

        call_args = qdrant_connector._client.upsert.call_args[1]
        stored_metadata = call_args['points'][0].payload['metadata']
        assert stored_metadata == special_metadata

    @pytest.mark.asyncio
    async def test_zero_limit_search(self, qdrant_connector):
        qdrant_connector._client.collection_exists = AsyncMock(return_value=True)
        qdrant_connector._client.query_points = AsyncMock(
            return_value=MagicMock(points=[])
        )

        result = await qdrant_connector.search("test query", "test_collection", limit=0)

        call_args = qdrant_connector._client.query_points.call_args[1]
        assert call_args['limit'] == 0
        assert len(result.points) == 0

    @pytest.mark.asyncio
    async def test_negative_limit_search(self, qdrant_connector):
        qdrant_connector._client.collection_exists = AsyncMock(return_value=True)
        qdrant_connector._client.query_points = AsyncMock(
            return_value=MagicMock(points=[])
        )

        await qdrant_connector.search("test query", "test_collection", limit=-1)

        call_args = qdrant_connector._client.query_points.call_args[1]
        assert call_args['limit'] == -1

    def test_entry_with_none_content(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            Entry(content=None)

    @pytest.mark.asyncio
    async def test_collection_name_edge_cases(self, qdrant_connector):
        edge_case_names = [
            "collection-with-dashes",
            "collection_with_underscores",
            "collection123",
            "a",  # Single character
        ]

        qdrant_connector._client.collection_exists = AsyncMock(return_value=True)
        qdrant_connector._client.query_points = AsyncMock(
            return_value=MagicMock(points=[])
        )

        for collection_name in edge_case_names:
            await qdrant_connector.search("test", collection_name)

            call_args = qdrant_connector._client.query_points.call_args[1]
            assert call_args['collection_name'] == collection_name


class TestFixtureIntegration:
    async def test_error_handling_with_mock_client(self, mock_config, mock_embedding_provider):
        connector = QdrantConnector(mock_config, mock_embedding_provider)

        # Test that connection errors are properly propagated
        # This will fail because we're not running a real Qdrant instance
        try:
            await connector.get_collection_names()
            assert False, "Expected an exception"
        except Exception as e:
            assert "connection" in str(e).lower() or "api" in str(e).lower() or "failed" in str(e).lower() or "ssl" in str(e).lower()

    async def test_performance_data_batch_processing(self, mock_async_qdrant_client, performance_test_data, mock_config, mock_embedding_provider):
        """Test handling of large datasets."""
        connector = QdrantConnector(mock_config, mock_embedding_provider)
        connector.client = mock_async_qdrant_client

        mock_async_qdrant_client.collection_exists.return_value = True
        mock_async_qdrant_client.upsert.return_value = MagicMock()

        collection_name = "performance_test"
        for entry in performance_test_data[:5]:  # Test with first 5 entries to keep test fast
            await connector.store(entry, collection_name)

        assert mock_async_qdrant_client.upsert.call_count == 5

    def test_multilingual_entries_fixture(self, multilingual_entries):
        assert len(multilingual_entries) == 4

        contents = [entry.content for entry in multilingual_entries]
        assert any("Hello" in content for content in contents)
        assert any("Privet" in content or "world" in content.lower() for content in contents)

        languages = [entry.metadata["language"] for entry in multilingual_entries]
        assert "en" in languages
        assert "ru" in languages
        assert "es" in languages
        assert "ja" in languages

    def test_performance_data_fixture(self, performance_test_data):
        assert len(performance_test_data) == 100

        first_entry = performance_test_data[0]
        assert "Performance test document" in first_entry.content
        assert "Lorem ipsum" in first_entry.content
        assert "doc_id" in first_entry.metadata
        assert "batch" in first_entry.metadata
        assert "category" in first_entry.metadata
        assert "size" in first_entry.metadata


if __name__ == "__main__":
    pytest.main([__file__])
