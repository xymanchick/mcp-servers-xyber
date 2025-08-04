import logging
from enum import Enum
from typing import Any

from mcp_server_qdrant.qdrant.embeddings.types import EmbeddingProviderType
from pydantic import BaseModel, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# --- Configuration and Error Classes --- #


class QdrantServiceError(Exception):
    """Base class for Qdrant service-related errors."""

    pass


class QdrantConfigError(QdrantServiceError):
    """Configuration-related errors for Qdrant client."""

    pass


class QdrantAPIError(QdrantServiceError):
    """Errors during Qdrant API operations."""

    pass


# --- Qdrant Configuration Models --- #


class PayloadIndexType(str, Enum):
    """Supported payload index types."""

    KEYWORD = "keyword"
    INTEGER = "integer"
    FLOAT = "float"
    GEO = "geo"
    TEXT = "text"
    BOOL = "bool"
    DATETIME = "datetime"


class PayloadIndexConfig(BaseModel):
    """Configuration for a single payload index."""

    field_name: str = Field(
        ..., description="The field path to index (e.g., 'metadata.user_id')"
    )
    index_type: PayloadIndexType = Field(
        default=PayloadIndexType.KEYWORD, description="Type of payload index"
    )
    is_tenant: bool = Field(
        default=False,
        description="Whether this is a tenant key (only for KEYWORD type)",
    )

    def model_post_init(self, __context: Any) -> None:
        """Validate that is_tenant is only used with KEYWORD type."""
        if self.is_tenant and self.index_type != PayloadIndexType.KEYWORD:
            raise ValueError("is_tenant=True can only be used with KEYWORD index type")


class HnswConfig(BaseModel):
    """HNSW algorithm configuration."""

    m: int = Field(
        default=16,
        ge=0,
        description="Max connections per node. Set to 0 to disable global HNSW index",
    )
    ef_construct: int = Field(
        default=200, ge=4, description="Size of the dynamic candidate list"
    )
    payload_m: int | None = Field(
        default=None,
        ge=0,
        description="HNSW connections for tenant partitions (when m=0)",
    )

    def model_post_init(self, __context: Any) -> None:
        """Validate HNSW configuration."""
        if self.m == 0 and self.payload_m is None:
            logger.warning(
                "HNSW m=0 (disabled global index) without payload_m may result in poor performance. "
                "Consider setting payload_m to a positive value (e.g., 16) for multi-tenant setups."
            )


class CollectionConfig(BaseModel):
    """Configuration for collection creation and indexing."""

    hnsw_config: HnswConfig = Field(
        default_factory=HnswConfig, description="HNSW algorithm settings"
    )
    payload_indexes: list[PayloadIndexConfig] = Field(
        default_factory=list, description="Payload indexes to create"
    )

    @model_validator(mode="before")
    @classmethod
    def convert_dict_to_list(cls, data: Any) -> Any:
        """Convert dictionary with numeric keys to list for payload_indexes."""
        if isinstance(data, dict) and "payload_indexes" in data:
            payload_indexes = data["payload_indexes"]
            if isinstance(payload_indexes, dict):
                # Check if all keys are numeric strings
                try:
                    numeric_keys = [int(k) for k in payload_indexes.keys()]
                    # Sort by numeric key and convert to list
                    sorted_items = sorted(
                        payload_indexes.items(), key=lambda x: int(x[0])
                    )
                    data["payload_indexes"] = [item[1] for item in sorted_items]
                except (ValueError, TypeError):
                    # If not all keys are numeric, leave as is (will fail validation)
                    pass
        return data

    def model_post_init(self, __context: Any) -> None:
        """Validate collection configuration consistency."""
        # Check that only one payload index has is_tenant=True
        tenant_count = sum(1 for idx in self.payload_indexes if idx.is_tenant)
        if tenant_count > 1:
            raise ValueError("Only one payload index can have is_tenant=True")

        # If there's a tenant index, ensure HNSW is configured for multi-tenant
        if tenant_count == 1 and self.hnsw_config.m != 0:
            raise ValueError(
                "When using tenant-based indexing (is_tenant=True), HNSW m must be set to 0 "
                "to disable global index. Consider setting payload_m for tenant-specific indexing."
            )


class EmbeddingProviderSettings(BaseSettings):
    """
    Configuration for the embedding provider.
    """

    model_config = SettingsConfigDict(
        env_prefix="EMBEDDING_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    provider_type: EmbeddingProviderType = Field(
        default=EmbeddingProviderType.FASTEMBED,
        validation_alias="PROVIDER",
    )
    model_name: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        validation_alias="MODEL",
    )


class QdrantConfig(BaseSettings):
    """
    Configuration for connecting to Qdrant vector database service.
    Reads from environment variables prefixed with QDRANT_.
    """

    model_config = SettingsConfigDict(
        env_prefix="QDRANT_",
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
        case_sensitive=False,
    )

    # Connection settings
    host: str = "localhost"  # Qdrant server host
    port: int = 6333  # REST API port
    grpc_port: int = 6334  # gRPC API port (optional)
    api_key: str | None = None  # API key for cloud deployments
    local_path: str | None = None  # Local path for storage (alternative to host/port)

    # Collection configuration
    collection_config: CollectionConfig = Field(
        default_factory=CollectionConfig,
        description="Default configuration for new collections",
    )

    @model_validator(mode="after")
    def empty_string_to_none(self) -> "QdrantConfig":
        """Convert empty strings to None for all fields with None in their type annotation."""
        for field_name, field in self.__class__.model_fields.items():
            # Check if field type annotation includes None
            annotation = getattr(field, "annotation", None)
            if annotation is None:
                continue

            # Check if it's a union type that includes None
            has_none_type = False
            if hasattr(annotation, "__args__"):
                has_none_type = type(None) in annotation.__args__

            # If field can be None and current value is empty string, convert to None
            if has_none_type:
                value = getattr(self, field_name, None)
                if isinstance(value, str) and value == "":
                    setattr(self, field_name, None)

        return self

    @property
    def location(self) -> str:
        """Return the location string for Qdrant client."""
        if not self.host:
            return ""
        return f"{self.host}:{self.port}"
