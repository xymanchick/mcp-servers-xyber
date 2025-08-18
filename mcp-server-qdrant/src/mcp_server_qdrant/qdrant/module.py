import logging
import uuid
from collections.abc import Sequence
from functools import lru_cache
from typing import Any

from mcp_server_qdrant.qdrant.config import (
    EmbeddingProviderSettings,
    PayloadIndexConfig,
    PayloadIndexType,
    QdrantAPIError,
    QdrantConfig,
)
from mcp_server_qdrant.qdrant.embeddings.base import EmbeddingProvider
from mcp_server_qdrant.qdrant.embeddings.factory import create_embedding_provider
from pydantic import BaseModel
from qdrant_client import AsyncQdrantClient, models
from qdrant_client.models import CollectionInfo

logger = logging.getLogger(__name__)

# --- Type Definitions --- #

Metadata = dict[str, Any]


class Entry(BaseModel):
    """
    A single entry in the Qdrant collection.
    """

    content: str
    metadata: Metadata | None = None

    def __str__(self) -> str:
        """
        Return a string representation of the entry.
        """
        return f"Entry(content={self.content}, metadata={self.metadata})"


# --- Main Service Class --- #


class QdrantConnector:
    """
    Encapsulates the connection to a Qdrant server and all the methods to interact with it.
    """

    def __init__(
        self,
        config: QdrantConfig,
        embedding_provider: EmbeddingProvider,
    ):
        """
        Initialize the Qdrant connector.

        Args:
            config: The Qdrant configuration
            embedding_provider: The embedding provider to use

        """
        self._config = config
        self._embedding_provider = embedding_provider
        self._client = AsyncQdrantClient(
            location=config.location, api_key=config.api_key, path=config.local_path
        )
        logger.info(
            f"Initialized Qdrant connector: location={config.location or 'local'}"
        )

    async def get_collection_names(self) -> list[str]:
        """
        Get the names of all collections in the Qdrant server.

        Returns:
            A list of collection names

        """
        response = await self._client.get_collections()
        return [collection.name for collection in response.collections]

    async def get_collection_details(self, collection_name: str) -> CollectionInfo:
        """
        Retrieves detailed configuration information for a specific collection.

        Args:
            collection_name: The name of the collection.

        Returns:
            A dictionary summarizing the collection's configuration.

        Raises:
            QdrantAPIError: If the collection does not exist or an API error occurs.

        """
        try:
            collection_info = await self._client.get_collection(
                collection_name=collection_name
            )
            return collection_info

        except Exception as e:
            logger.error(
                f"Error retrieving details for collection '{collection_name}': {e}",
                exc_info=True,
            )
            err_str = str(e).lower()
            if (
                "not found" in err_str
                or "status_code=404" in err_str
                or "statuscode.not_found" in err_str
            ):
                raise QdrantAPIError(
                    f"Collection '{collection_name}' not found."
                ) from e
            raise QdrantAPIError(
                f"Failed to get details for collection '{collection_name}': {str(e)}"
            ) from e

    async def store(self, entry: Entry, collection_name: str) -> None:
        """
        Store information in the Qdrant collection with metadata.

        Args:
            entry: The entry to store (content + metadata)
            collection_name: The collection name

        Raises:
            QdrantAPIError: If there's an issue storing the entry

        """
        try:
            # Create the collection if it doesn't exist (with configured settings)
            await self._ensure_collection_exists(collection_name)

            # Embed the document
            embeddings = await self._embedding_provider.embed_documents([entry.content])

            # Add to Qdrant
            vector_name = self._embedding_provider.get_vector_name()
            payload = {"document": entry.content, "metadata": entry.metadata}

            await self._client.upsert(
                collection_name=collection_name,
                points=[
                    models.PointStruct(
                        id=uuid.uuid4().hex,
                        vector={vector_name: embeddings[0]},
                        payload=payload,
                    )
                ],
            )
            logger.debug(f"Stored {entry} in collection '{collection_name}'")

        except Exception as e:
            error_msg = f"Failed to store entry in Qdrant: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise QdrantAPIError(error_msg) from e

    async def search(
        self,
        query: str,
        collection_name: str,
        limit: int = 10,
        filters: dict[str, Any] | None = None,
        with_payload: bool | list[str] | models.PayloadSelector | None = True,
        with_vectors: bool | Sequence[str] | None = False,
    ) -> models.QueryResponse:
        """
        Find entries in the Qdrant collection by semantic similarity.

        Args:
            query: The search query
            collection_name: The name of the collection.
            limit: Max number of results.
            filters: Optional dictionary of field_path -> value for filtering.
                    Can include tenant fields, indexed fields, or any other payload fields.
                    Example: {"metadata.user_id": "alice", "metadata.category": "work"}
            with_payload: Whether to include payload in results.
                          Can be bool, list of keys, or a PayloadSelector. Defaults to True.
            with_vectors: Whether to include vectors in results.
                          Can be bool or list of vector names. Defaults to False.

        Returns:
            List of ScoredPoint objects found. Empty list if none or collection doesn't exist.

        Raises:
            QdrantAPIError: If there's an issue searching the entries.

        """
        try:
            collection_exists = await self._client.collection_exists(collection_name)
            if not collection_exists:
                # Get available collections to include in error message
                available_collections = await self.get_collection_names()
                collections_list = (
                    ", ".join(f"'{name}'" for name in available_collections)
                    if available_collections
                    else "none"
                )

                error_msg = (
                    f"Collection '{collection_name}' does not exist. "
                    f"Available collections: {collections_list}"
                )
                logger.warning(error_msg)
                raise QdrantAPIError(error_msg)

            # Embed the query
            query_vector = await self._embedding_provider.embed_query(query)
            vector_name = self._embedding_provider.get_vector_name()

            query_filter: models.Filter | None = None
            if filters:
                # Build filter conditions from the filters dict
                filter_conditions: list[models.Condition] = []
                for field_path, value in filters.items():
                    if value is not None:
                        filter_conditions.append(
                            models.FieldCondition(
                                key=field_path,
                                match=models.MatchValue(value=value),
                            )
                        )

                if filter_conditions:
                    query_filter = models.Filter(must=filter_conditions)

            search_results = await self._client.query_points(
                collection_name=collection_name,
                query=query_vector,
                query_filter=query_filter,
                limit=limit,
                using=vector_name,
                with_payload=with_payload,
                with_vectors=with_vectors,
            )

            logger.debug(
                f"Found {search_results} results for query in '{collection_name}'"
                f"{f' with filters {filters}' if query_filter else ''}."
            )

            return search_results
        except Exception as e:
            error_msg = f"Failed to search in Qdrant: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise QdrantAPIError(error_msg) from e

    async def _ensure_collection_exists(self, collection_name: str) -> None:
        """
        Ensure that the collection exists, creating it with configured settings if necessary.

        Args:
            collection_name: The collection name to check/create

        """
        collection_exists = await self._client.collection_exists(collection_name)
        if not collection_exists:
            await self._create_configured_collection(collection_name)
        else:
            await self._ensure_payload_indexes(collection_name)

    async def _create_configured_collection(self, collection_name: str) -> None:
        """
        Create a new collection with the configured HNSW and vector settings.

        Args:
            collection_name: The collection name to create

        Raises:
            QdrantAPIError: If collection or payload index creation fails

        """
        try:
            vector_size = self._embedding_provider.get_vector_size()
            vector_name = self._embedding_provider.get_vector_name()

            # Build HNSW config from settings
            hnsw_config_dict: dict[str, int] = {}
            hnsw_config_dict["m"] = self._config.collection_config.hnsw_config.m
            hnsw_config_dict["ef_construct"] = (
                self._config.collection_config.hnsw_config.ef_construct
            )
            hnsw_config_dict["payload_m"] = (
                self._config.collection_config.hnsw_config.payload_m
            )

            hnsw_config = models.HnswConfigDiff(**hnsw_config_dict)

            await self._client.create_collection(
                collection_name=collection_name,
                vectors_config={
                    vector_name: models.VectorParams(
                        size=vector_size,
                        distance=models.Distance.COSINE,
                    )
                },
                hnsw_config=hnsw_config,
            )

            logger.info(
                f"Created new collection '{collection_name}' with HNSW config: {hnsw_config_dict or 'default'}"
            )

            # Create payload indexes as configured
            await self._ensure_payload_indexes(collection_name)

        except Exception as e:
            logger.error(f"Failed to create collection '{collection_name}': {e}")
            raise QdrantAPIError(
                f"Failed to create collection '{collection_name}': {e}"
            ) from e

    async def _ensure_payload_indexes(self, collection_name: str) -> None:
        """
        Ensure all configured payload indexes exist for the collection.

        Args:
            collection_name: The collection name

        Raises:
            QdrantAPIError: If any payload index creation fails

        """
        for index_config in self._config.collection_config.payload_indexes:
            await self._create_payload_index(collection_name, index_config)

    async def _create_payload_index(
        self, collection_name: str, index_config: PayloadIndexConfig
    ) -> None:
        """
        Create a single payload index according to the configuration.

        Args:
            collection_name: The collection name
            index_config: The payload index configuration

        """
        try:
            # Map our config enum to Qdrant's PayloadSchemaType
            type_mapping = {
                PayloadIndexType.KEYWORD: models.PayloadSchemaType.KEYWORD,
                PayloadIndexType.INTEGER: models.PayloadSchemaType.INTEGER,
                PayloadIndexType.FLOAT: models.PayloadSchemaType.FLOAT,
                PayloadIndexType.GEO: models.PayloadSchemaType.GEO,
                PayloadIndexType.TEXT: models.PayloadSchemaType.TEXT,
                PayloadIndexType.BOOL: models.PayloadSchemaType.BOOL,
                PayloadIndexType.DATETIME: models.PayloadSchemaType.DATETIME,
            }

            # For keyword indexes with is_tenant=True, use KeywordIndexParams directly
            if (
                index_config.index_type == PayloadIndexType.KEYWORD
                and index_config.is_tenant
            ):
                field_schema = models.KeywordIndexParams(
                    type=models.KeywordIndexType.KEYWORD, is_tenant=True
                )
            else:
                # Use the basic schema type for all other cases
                field_schema = type_mapping[index_config.index_type]

            await self._client.create_payload_index(
                collection_name=collection_name,
                field_name=index_config.field_name,
                field_schema=field_schema,
                wait=True,
            )

            logger.info(
                f"Created payload index for field '{index_config.field_name}' "
                f"(type: {index_config.index_type.value}"
                f"{', is_tenant=True' if index_config.is_tenant else ''}) "
                f"on collection '{collection_name}'"
            )

        except Exception as e:
            logger.error(
                f"Failed to create payload index '{index_config.field_name}' on collection '{collection_name}': {e}"
            )
            raise QdrantAPIError(
                f"Failed to create payload index '{index_config.field_name}' on collection '{collection_name}': {e}"
            ) from e


@lru_cache(maxsize=1)
def get_qdrant_connector() -> QdrantConnector:
    """
    Get a singleton instance of the QdrantConnector.

    The connector is created with default configuration from environment
    variables and cached for reuse.

    Returns:
        QdrantConnector instance

    """
    config = QdrantConfig()
    embedding_provider_settings = EmbeddingProviderSettings()
    embedding_provider = create_embedding_provider(embedding_provider_settings)
    return QdrantConnector(config, embedding_provider)
