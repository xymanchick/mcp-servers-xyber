import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from typing import Any, Dict, List

from fastmcp import Context
from fastmcp.exceptions import ToolError
from pydantic import ValidationError as PydanticValidationError
from qdrant_client.models import CollectionInfo, ScoredPoint

from mcp_server_qdrant.exceptions import ValidationError
from mcp_server_qdrant.server import app_lifespan, mcp_server
from mcp_server_qdrant.tools import (
    qdrant_store_logic,
    qdrant_find_logic,
    qdrant_get_collection_info_logic,
    qdrant_get_collections_logic,
)


class TestQdrantStore:
    @pytest.mark.asyncio
    async def test_store_success_with_metadata(
        self,
        mock_qdrant_connector: AsyncMock,
        valid_store_request: Dict[str, Any]
    ):
        result = await qdrant_store_logic(mock_qdrant_connector, valid_store_request)

        assert "Remembered:" in result
        assert valid_store_request["information"] in result
        assert valid_store_request["collection_name"] in result
        mock_qdrant_connector.store.assert_called_once()

        call_args = mock_qdrant_connector.store.call_args
        entry = call_args[0][0]  # First positional argument
        assert entry.content == valid_store_request["information"]
        assert entry.metadata == valid_store_request["metadata"]

        assert call_args[1]["collection_name"] == valid_store_request["collection_name"]

    @pytest.mark.asyncio
    async def test_store_success_without_metadata(
        self,
        mock_qdrant_connector: AsyncMock
    ):
        request = {
            "collection_name": "test_collection",
            "information": "Test information without metadata"
        }

        result = await qdrant_store_logic(mock_qdrant_connector, request)

        assert "Remembered:" in result
        assert request["information"] in result
        mock_qdrant_connector.store.assert_called_once()

        call_args = mock_qdrant_connector.store.call_args
        entry = call_args[0][0]
        assert entry.content == request["information"]
        assert entry.metadata is None

    @pytest.mark.asyncio
    async def test_store_with_complex_metadata(
        self,
        mock_qdrant_connector: AsyncMock
    ):
        complex_request = {
            "collection_name": "test_collection",
            "information": "Complex test information with nested metadata",
            "metadata": {
                "user_id": "user123",
                "category": "research",
                "tags": ["ai", "ml", "nlp"],
                "numeric_value": 42.5,
                "nested": {
                    "level1": {
                        "level2": "deep_value",
                        "array": [1, 2, 3]
                    }
                },
                "boolean_flag": True
            }
        }

        result = await qdrant_store_logic(mock_qdrant_connector, complex_request)

        assert "Remembered:" in result
        mock_qdrant_connector.store.assert_called_once()

        call_args = mock_qdrant_connector.store.call_args
        entry = call_args[0][0]
        assert entry.metadata == complex_request["metadata"]

    @pytest.mark.asyncio
    async def test_store_validation_errors(
        self,
        mock_qdrant_connector: AsyncMock,
        invalid_requests: Dict[str, Dict[str, Any]]
    ):
        with pytest.raises(ValidationError):
            await qdrant_store_logic(
                mock_qdrant_connector,
                invalid_requests["store_missing_collection"]
            )

        with pytest.raises(ValidationError):
            await qdrant_store_logic(
                mock_qdrant_connector,
                invalid_requests["store_wrong_type_collection"]
            )

        with pytest.raises(ValidationError):
            await qdrant_store_logic(
                mock_qdrant_connector,
                invalid_requests["store_missing_information"]
            )

        mock_qdrant_connector.store.assert_not_called()

    @pytest.mark.asyncio
    async def test_store_connector_error_handling(
        self,
        mock_qdrant_connector: AsyncMock,
        valid_store_request: Dict[str, Any]
    ):
        mock_qdrant_connector.store.side_effect = Exception("Database connection failed")

        with pytest.raises(ToolError) as exc_info:
            await qdrant_store_logic(mock_qdrant_connector, valid_store_request)

        assert "Error storing information: Database connection failed" in str(exc_info.value)
        mock_qdrant_connector.store.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_large_information(
        self,
        mock_qdrant_connector: AsyncMock
    ):
        large_content = "Large content: " + "x" * 10000  # 10KB+ content
        request = {
            "collection_name": "test_collection",
            "information": large_content,
            "metadata": {"size": "large", "type": "test"}
        }

        result = await qdrant_store_logic(mock_qdrant_connector, request)

        assert "Remembered:" in result
        assert large_content in result
        mock_qdrant_connector.store.assert_called_once()

        call_args = mock_qdrant_connector.store.call_args
        entry = call_args[0][0]
        assert entry.content == large_content


class TestQdrantFind:
    @pytest.mark.asyncio
    async def test_find_success_with_results(
        self,
        mock_qdrant_connector: AsyncMock,
        valid_find_request: Dict[str, Any],
        sample_scored_points: List[ScoredPoint]
    ):
        mock_search_result = MagicMock()
        mock_search_result.points = sample_scored_points
        mock_qdrant_connector.search.return_value = mock_search_result

        result = await qdrant_find_logic(mock_qdrant_connector, valid_find_request)

        assert result == sample_scored_points
        mock_qdrant_connector.search.assert_called_once_with(
            valid_find_request["query"],
            collection_name=valid_find_request["collection_name"],
            limit=valid_find_request["search_limit"],
            filters=valid_find_request["filters"]
        )

    @pytest.mark.asyncio
    async def test_find_no_results(
        self,
        mock_qdrant_connector: AsyncMock
    ):
        request = {
            "collection_name": "test_collection",
            "query": "nonexistent query that should return no results",
            "search_limit": 5
        }

        mock_qdrant_connector.search.return_value = None

        result = await qdrant_find_logic(mock_qdrant_connector, request)

        assert isinstance(result, str)
        assert "No information found for the query" in result
        assert request["query"] in result

    @pytest.mark.asyncio
    async def test_find_empty_results(
        self,
        mock_qdrant_connector: AsyncMock
    ):
        request = {
            "collection_name": "test_collection",
            "query": "empty results query"
        }

        mock_search_result = MagicMock()
        mock_search_result.points = []
        mock_qdrant_connector.search.return_value = mock_search_result

        result = await qdrant_find_logic(mock_qdrant_connector, request)

        assert result == []

    @pytest.mark.asyncio
    async def test_find_with_default_values(
        self,
        mock_qdrant_connector: AsyncMock,
        sample_scored_points: List[ScoredPoint]
    ):
        request = {
            "collection_name": "test_collection",
            "query": "test query with defaults"
            # search_limit and filters will use defaults
        }

        mock_search_result = MagicMock()
        mock_search_result.points = sample_scored_points
        mock_qdrant_connector.search.return_value = mock_search_result

        result = await qdrant_find_logic(mock_qdrant_connector, request)

        assert result == sample_scored_points
        mock_qdrant_connector.search.assert_called_once_with(
            "test query with defaults",
            collection_name="test_collection",
            limit=10,  # Default value
            filters=None  # Default value
        )

    @pytest.mark.asyncio
    async def test_find_with_complex_filters(
        self,
        mock_qdrant_connector: AsyncMock,
        sample_scored_points: List[ScoredPoint]
    ):
        request = {
            "collection_name": "test_collection",
            "query": "complex filter query",
            "search_limit": 15,
            "filters": {
                "user_id": "user123",
                "category": ["ai", "ml", "nlp"],
                "priority": "high",
                "date_range": {
                    "start": "2023-01-01",
                    "end": "2023-12-31"
                },
                "numeric_threshold": {"gte": 0.8}
            }
        }

        mock_search_result = MagicMock()
        mock_search_result.points = sample_scored_points
        mock_qdrant_connector.search.return_value = mock_search_result

        result = await qdrant_find_logic(mock_qdrant_connector, request)

        assert result == sample_scored_points
        mock_qdrant_connector.search.assert_called_once_with(
            request["query"],
            collection_name=request["collection_name"],
            limit=request["search_limit"],
            filters=request["filters"]
        )

    @pytest.mark.asyncio
    async def test_find_validation_errors(
        self,
        mock_qdrant_connector: AsyncMock,
        invalid_requests: Dict[str, Dict[str, Any]]
    ):
        with pytest.raises(ValidationError):
            await qdrant_find_logic(
                mock_qdrant_connector,
                invalid_requests["find_missing_query"]
            )

        with pytest.raises(ValidationError):
            await qdrant_find_logic(
                mock_qdrant_connector,
                invalid_requests["find_invalid_limit"]
            )

        mock_qdrant_connector.search.assert_not_called()

    @pytest.mark.asyncio
    async def test_find_connector_error_handling(
        self,
        mock_qdrant_connector: AsyncMock,
        valid_find_request: Dict[str, Any]
    ):
        mock_qdrant_connector.search.side_effect = Exception("Search index corrupted")

        with pytest.raises(ToolError) as exc_info:
            await qdrant_find_logic(mock_qdrant_connector, valid_find_request)

        assert "Error searching Qdrant: Search index corrupted" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_find_large_search_limit(
        self,
        mock_qdrant_connector: AsyncMock,
        sample_scored_points: List[ScoredPoint]
    ):
        request = {
            "collection_name": "test_collection",
            "query": "test query with large limit",
            "search_limit": 10000  # Very large limit
        }

        mock_search_result = MagicMock()
        mock_search_result.points = sample_scored_points
        mock_qdrant_connector.search.return_value = mock_search_result

        result = await qdrant_find_logic(mock_qdrant_connector, request)

        assert result == sample_scored_points
        mock_qdrant_connector.search.assert_called_once_with(
            "test query with large limit",
            collection_name="test_collection",
            limit=10000,
            filters=None
        )


class TestQdrantGetCollectionInfo:
    @pytest.mark.asyncio
    async def test_get_collection_info_success(
        self,
        mock_qdrant_connector: AsyncMock,
        valid_collection_info_request: Dict[str, Any],
        sample_collection_info: CollectionInfo
    ):
        mock_qdrant_connector.get_collection_details.return_value = sample_collection_info

        result = await qdrant_get_collection_info_logic(
            mock_qdrant_connector,
            valid_collection_info_request
        )

        assert result == sample_collection_info
        mock_qdrant_connector.get_collection_details.assert_called_once_with(
            valid_collection_info_request["collection_name"]
        )

    @pytest.mark.asyncio
    async def test_get_collection_info_detailed_verification(
        self,
        mock_qdrant_connector: AsyncMock
    ):
        request = {"collection_name": "detailed_test_collection"}

        expected_info = MagicMock(spec=CollectionInfo)
        expected_info.status = "green"
        expected_info.vectors_count = 2500
        expected_info.segments_count = 5
        expected_info.disk_data_size = 5242880  # 5MB
        expected_info.ram_data_size = 1048576   # 1MB
        expected_info.payload_schema = {
            "user_id": "keyword",
            "category": "keyword",
            "tags": "keyword",
            "created_at": "keyword",
            "priority": "keyword"
        }

        mock_qdrant_connector.get_collection_details.return_value = expected_info

        result = await qdrant_get_collection_info_logic(mock_qdrant_connector, request)

        assert result.status == "green"
        assert result.vectors_count == 2500
        assert result.segments_count == 5
        assert result.disk_data_size == 5242880
        assert result.ram_data_size == 1048576
        assert "user_id" in result.payload_schema

    @pytest.mark.asyncio
    async def test_get_collection_info_validation_errors(
        self,
        mock_qdrant_connector: AsyncMock,
        invalid_requests: Dict[str, Dict[str, Any]]
    ):
        with pytest.raises(ValidationError):
            await qdrant_get_collection_info_logic(
                mock_qdrant_connector,
                invalid_requests["collection_info_missing_name"]
            )

        with pytest.raises(ValidationError):
            await qdrant_get_collection_info_logic(
                mock_qdrant_connector,
                invalid_requests["collection_info_wrong_type"]
            )

        mock_qdrant_connector.get_collection_details.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_collection_info_connector_error_returns_error_dict(
        self,
        mock_qdrant_connector: AsyncMock,
        valid_collection_info_request: Dict[str, Any]
    ):
        mock_qdrant_connector.get_collection_details.side_effect = Exception(
            "Collection 'test_collection' not found"
        )

        result = await qdrant_get_collection_info_logic(
            mock_qdrant_connector,
            valid_collection_info_request
        )

        assert isinstance(result, dict)
        assert "error" in result
        assert "Collection 'test_collection' not found" in result["error"]
        assert valid_collection_info_request["collection_name"] in result["error"]

    @pytest.mark.asyncio
    async def test_get_collection_info_with_special_collection_names(
        self,
        mock_qdrant_connector: AsyncMock,
        sample_collection_info: CollectionInfo
    ):
        special_names = [
            "collection-with-dashes",
            "collection_with_underscores",
            "collection123",
            "UPPERCASE_COLLECTION",
            "mixed_Case_Collection"
        ]

        mock_qdrant_connector.get_collection_details.return_value = sample_collection_info

        for collection_name in special_names:
            request = {"collection_name": collection_name}

            result = await qdrant_get_collection_info_logic(mock_qdrant_connector, request)

            assert result == sample_collection_info

        assert mock_qdrant_connector.get_collection_details.call_count == len(special_names)


class TestQdrantGetCollections:
    @pytest.mark.asyncio
    async def test_get_collections_success(
        self,
        mock_qdrant_connector: AsyncMock
    ):
        expected_collections = [
            "documents",
            "images",
            "user_profiles",
            "product_catalog",
            "research_papers"
        ]
        mock_qdrant_connector.get_collection_names.return_value = expected_collections

        result = await qdrant_get_collections_logic(mock_qdrant_connector)

        assert result == expected_collections
        assert len(result) == 5
        mock_qdrant_connector.get_collection_names.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_collections_empty_database(
        self,
        mock_qdrant_connector: AsyncMock
    ):
        mock_qdrant_connector.get_collection_names.return_value = []

        result = await qdrant_get_collections_logic(mock_qdrant_connector)

        assert result == []
        assert len(result) == 0
        mock_qdrant_connector.get_collection_names.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_collections_single_collection(
        self,
        mock_qdrant_connector: AsyncMock
    ):
        expected_collections = ["single_collection"]
        mock_qdrant_connector.get_collection_names.return_value = expected_collections

        result = await qdrant_get_collections_logic(mock_qdrant_connector)

        assert result == expected_collections
        assert len(result) == 1
        assert result[0] == "single_collection"

    @pytest.mark.asyncio
    async def test_get_collections_connector_error_handling(
        self,
        mock_qdrant_connector: AsyncMock
    ):
        mock_qdrant_connector.get_collection_names.side_effect = Exception(
            "Database connection timeout"
        )

        with pytest.raises(ToolError) as exc_info:
            await qdrant_get_collections_logic(mock_qdrant_connector)

        assert "Error getting collection names: Database connection timeout" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_collections_with_special_names(
        self,
        mock_qdrant_connector: AsyncMock
    ):
        special_collections = [
            "collection-with-dashes",
            "collection_with_underscores",
            "collection123",
            "UPPERCASE_COLLECTION",
            "mixedCaseCollection",
            "collection.with.dots"
        ]
        mock_qdrant_connector.get_collection_names.return_value = special_collections

        result = await qdrant_get_collections_logic(mock_qdrant_connector)

        assert result == special_collections
        assert len(result) == 6
        assert all(isinstance(name, str) for name in result)


class TestServerLifecycle:
    @pytest.mark.asyncio
    async def test_app_lifespan_successful_initialization(self):
        mock_server = MagicMock()
        mock_connector = MagicMock()

        with patch('mcp_server_qdrant.server.get_qdrant_connector',
                  return_value=mock_connector) as mock_get_connector:

            async with app_lifespan(mock_server) as context:
                assert "qdrant_connector" in context
                assert context["qdrant_connector"] == mock_connector

                mock_get_connector.assert_called_once()

    @pytest.mark.asyncio
    async def test_app_lifespan_initialization_error(self):
        mock_server = MagicMock()

        with patch('mcp_server_qdrant.server.get_qdrant_connector',
                  side_effect=ConnectionError("Failed to connect to Qdrant")) as mock_get_connector:

            with pytest.raises(ConnectionError) as exc_info:
                async with app_lifespan(mock_server):
                    pass  # Should not reach here

            assert "Failed to connect to Qdrant" in str(exc_info.value)
            mock_get_connector.assert_called_once()

    @pytest.mark.asyncio
    async def test_app_lifespan_cleanup_on_exception(self):
        mock_server = MagicMock()
        mock_connector = MagicMock()

        with patch('mcp_server_qdrant.server.get_qdrant_connector',
                  return_value=mock_connector):

            with pytest.raises(RuntimeError):
                async with app_lifespan(mock_server):
                    # Simulate an error during lifespan execution
                    raise RuntimeError("Simulated error during execution")


    @pytest.mark.asyncio
    async def test_app_lifespan_multiple_initialization_calls(self):
        mock_server1 = MagicMock()
        mock_server2 = MagicMock()
        mock_connector1 = MagicMock()
        mock_connector2 = MagicMock()

        with patch('mcp_server_qdrant.server.get_qdrant_connector',
                  side_effect=[mock_connector1, mock_connector2]) as mock_get_connector:

            async with app_lifespan(mock_server1) as context1:
                assert context1["qdrant_connector"] == mock_connector1

            async with app_lifespan(mock_server2) as context2:
                assert context2["qdrant_connector"] == mock_connector2

            assert mock_get_connector.call_count == 2


class TestMCPServerConfiguration:
    def test_mcp_server_instance_created(self):
        assert mcp_server is not None
        assert mcp_server.name == "qdrant"

    def test_mcp_server_has_correct_tools(self):
        assert mcp_server is not None
        assert hasattr(mcp_server, 'name')
        assert mcp_server.name == "qdrant"

    def test_tool_names_enum_values(self):
        from mcp_server_qdrant.server import ToolNames

        assert ToolNames.QDRANT_STORE == "qdrant-store"
        assert ToolNames.QDRANT_FIND == "qdrant-find"

        assert isinstance(ToolNames.QDRANT_STORE, str)
        assert isinstance(ToolNames.QDRANT_FIND, str)


class TestIntegrationScenarios:
    @pytest.mark.asyncio
    async def test_complete_document_management_workflow(
        self,
        mock_qdrant_connector: AsyncMock,
        sample_scored_points: List[ScoredPoint]
    ):
        """Test a complete workflow: store documents, search them, and get collection info."""
        # Step 1: Store multiple documents
        documents = [
            {
                "collection_name": "research_papers",
                "information": "Machine learning algorithms for natural language processing tasks",
                "metadata": {"author": "Dr. Smith", "year": 2023, "field": "AI"}
            },
            {
                "collection_name": "research_papers",
                "information": "Deep neural networks in computer vision applications",
                "metadata": {"author": "Dr. Johnson", "year": 2023, "field": "CV"}
            },
            {
                "collection_name": "research_papers",
                "information": "Quantum computing advances in optimization problems",
                "metadata": {"author": "Dr. Brown", "year": 2024, "field": "Quantum"}
            }
        ]

        # Store all documents
        for doc in documents:
            result = await qdrant_store_logic(mock_qdrant_connector, doc)
            assert "Remembered:" in result
            assert doc["information"] in result

        # Verify all store calls were made
        assert mock_qdrant_connector.store.call_count == 3

        # Step 2: Search for stored documents
        mock_search_result = MagicMock()
        mock_search_result.points = sample_scored_points
        mock_qdrant_connector.search.return_value = mock_search_result

        search_request = {
            "collection_name": "research_papers",
            "query": "machine learning neural networks",
            "search_limit": 10,
            "filters": {"year": 2023}
        }

        search_results = await qdrant_find_logic(mock_qdrant_connector, search_request)
        assert search_results == sample_scored_points
        assert mock_qdrant_connector.search.call_count == 1

        # Step 3: Get collection information
        mock_collection_info = MagicMock(spec=CollectionInfo)
        mock_collection_info.status = "green"
        mock_collection_info.vectors_count = 3  # Should reflect our 3 documents
        mock_qdrant_connector.get_collection_details.return_value = mock_collection_info

        collection_info_request = {"collection_name": "research_papers"}
        collection_info = await qdrant_get_collection_info_logic(
            mock_qdrant_connector,
            collection_info_request
        )

        assert collection_info.status == "green"
        assert collection_info.vectors_count == 3

    @pytest.mark.asyncio
    async def test_multi_collection_workflow(
        self,
        mock_qdrant_connector: AsyncMock,
        sample_scored_points: List[ScoredPoint]
    ):
        """Test workflow across multiple collections."""

        # Step 1: Get list of all collections
        mock_qdrant_connector.get_collection_names.return_value = [
            "research_papers", "user_documents", "product_catalog"
        ]

        collections = await qdrant_get_collections_logic(mock_qdrant_connector)
        assert len(collections) == 3
        assert "research_papers" in collections

        # Step 2: Store documents in different collections
        documents = [
            {
                "collection_name": "research_papers",
                "information": "Research paper about AI ethics",
                "metadata": {"type": "academic"}
            },
            {
                "collection_name": "user_documents",
                "information": "User manual for software application",
                "metadata": {"type": "documentation"}
            },
            {
                "collection_name": "product_catalog",
                "information": "Smartphone with advanced camera features",
                "metadata": {"type": "product", "category": "electronics"}
            }
        ]

        for doc in documents:
            result = await qdrant_store_logic(mock_qdrant_connector, doc)
            assert "Remembered:" in result

        # Step 3: Search in specific collection
        mock_search_result = MagicMock()
        mock_search_result.points = sample_scored_points[:1]  # Single result
        mock_qdrant_connector.search.return_value = mock_search_result

        search_request = {
            "collection_name": "product_catalog",
            "query": "smartphone camera",
            "filters": {"category": "electronics"}
        }

        search_results = await qdrant_find_logic(mock_qdrant_connector, search_request)
        assert len(search_results) == 1

    @pytest.mark.asyncio
    async def test_error_recovery_workflow(
        self,
        mock_qdrant_connector: AsyncMock
    ):
        """Test workflow with error conditions and recovery."""

        # Step 1: Try to store in non-existent collection (should work, but test error handling)
        store_request = {
            "collection_name": "new_collection",
            "information": "First document in new collection"
        }

        result = await qdrant_store_logic(mock_qdrant_connector, store_request)
        assert "Remembered:" in result

        # Step 2: Try to search in collection that has no documents
        mock_qdrant_connector.search.return_value = None  # No results

        search_request = {
            "collection_name": "empty_collection",
            "query": "non-existent document"
        }

        search_result = await qdrant_find_logic(mock_qdrant_connector, search_request)
        assert isinstance(search_result, str)
        assert "No information found" in search_result

        # Step 3: Try to get info for non-existent collection (should return error dict)
        mock_qdrant_connector.get_collection_details.side_effect = Exception(
            "Collection does not exist"
        )

        info_request = {"collection_name": "non_existent_collection"}
        info_result = await qdrant_get_collection_info_logic(mock_qdrant_connector, info_request)

        assert isinstance(info_result, dict)
        assert "error" in info_result


class TestEdgeCasesAndValidation:
    """Test edge cases, boundary conditions, and comprehensive validation scenarios."""

    @pytest.mark.asyncio
    async def test_extreme_input_sizes(
        self,
        mock_qdrant_connector: AsyncMock
    ):
        """Test handling of extremely large and small inputs."""

        # Test with very large information content
        large_content = "Large document content: " + "x" * 100000  # 100KB content
        large_request = {
            "collection_name": "large_documents",
            "information": large_content,
            "metadata": {"size": "extra_large", "words": 100000}
        }

        result = await qdrant_store_logic(mock_qdrant_connector, large_request)
        assert "Remembered:" in result

        # Test with minimal content
        minimal_request = {
            "collection_name": "minimal",
            "information": "a"  # Single character
        }

        result = await qdrant_store_logic(mock_qdrant_connector, minimal_request)
        assert "Remembered:" in result

    @pytest.mark.asyncio
    async def test_unicode_and_special_characters(
        self,
        mock_qdrant_connector: AsyncMock
    ):
        unicode_request = {
            "collection_name": "unicode_test",
            "information": "Test with emojis and Unicode: alphabeta, chinese, arabic, russian",
            "metadata": {
                "language": "multi",
                "symbols": "symbols",
                "math": "sum integral",
                "special": "!@#$%^&*()_+-=[]{}|;':\",./<>?"
            }
        }

        result = await qdrant_store_logic(mock_qdrant_connector, unicode_request)
        assert "Remembered:" in result

        # Verify the unicode content was passed correctly
        call_args = mock_qdrant_connector.store.call_args
        entry = call_args[0][0]
        assert "Unicode" in entry.content

    @pytest.mark.asyncio
    async def test_boundary_search_limits(
        self,
        mock_qdrant_connector: AsyncMock,
        sample_scored_points: List[ScoredPoint]
    ):
        """Test boundary conditions for search limits."""

        mock_search_result = MagicMock()
        mock_search_result.points = sample_scored_points
        mock_qdrant_connector.search.return_value = mock_search_result

        # Test minimum search limit
        min_request = {
            "collection_name": "test_collection",
            "query": "test query",
            "search_limit": 1
        }

        result = await qdrant_find_logic(mock_qdrant_connector, min_request)
        assert result == sample_scored_points

        # Test maximum reasonable search limit
        max_request = {
            "collection_name": "test_collection",
            "query": "test query",
            "search_limit": 1000
        }

        result = await qdrant_find_logic(mock_qdrant_connector, max_request)
        assert result == sample_scored_points

    @pytest.mark.asyncio
    async def test_complex_nested_metadata_validation(
        self,
        mock_qdrant_connector: AsyncMock
    ):
        """Test deeply nested and complex metadata structures."""

        complex_metadata = {
            "level1": {
                "level2": {
                    "level3": {
                        "level4": {
                            "deep_value": "nested_deep",
                            "array": [1, 2, {"nested_array_object": True}],
                            "mixed_types": [
                                "string",
                                42,
                                3.14,
                                True,
                                None,
                                {"key": "value"}
                            ]
                        }
                    }
                }
            },
            "parallel_structure": {
                "dates": ["2023-01-01", "2023-12-31"],
                "numbers": [1, 2, 3, 4, 5],
                "booleans": [True, False, True],
                "mixed_nested": {
                    "coordinates": {"x": 1.5, "y": 2.7, "z": 3.9},
                    "metadata_about_metadata": {
                        "created": "2023-01-01T00:00:00Z",
                        "creator": "test_system",
                        "version": "1.0.0"
                    }
                }
            }
        }

        complex_request = {
            "collection_name": "complex_metadata_test",
            "information": "Document with extremely complex metadata structure",
            "metadata": complex_metadata
        }

        result = await qdrant_store_logic(mock_qdrant_connector, complex_request)
        assert "Remembered:" in result

        call_args = mock_qdrant_connector.store.call_args
        entry = call_args[0][0]
        assert entry.metadata == complex_metadata
        assert entry.metadata["level1"]["level2"]["level3"]["level4"]["deep_value"] == "nested_deep"
