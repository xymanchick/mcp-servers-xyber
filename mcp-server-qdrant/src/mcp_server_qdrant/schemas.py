from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Base(BaseModel):
    """Base model for all schemas."""

    model_config = ConfigDict(
        strict=True, from_attributes=True, extra="forbid", populate_by_name=True
    )


class QdrantGetCollectionInfoRequest(Base):
    """Input schema for the qdrant-get-collection-info tool."""

    collection_name: str = Field(
        ..., description="The name of the collection to retrieve information from."
    )


class QdrantStoreRequest(QdrantGetCollectionInfoRequest):
    """Input schema for the qdrant-store tool."""

    information: str = Field(..., description="The information to store.")
    metadata: dict[str, Any] | None = Field(
        None, description="JSON metadata to store with the information, optional."
    )


class QdrantFindRequest(QdrantGetCollectionInfoRequest):
    """Input schema for the qdrant-find tool."""

    query: str = Field(..., description="The query to use for the search.")
    search_limit: int = Field(
        10, description="The maximum number of results to return."
    )
    filters: dict[str, Any] | None = Field(
        None,
        description="Optional filters as field_path -> value pairs. "
        "Filtering by tenant fields (if configured) will be much faster than filtering by other fields.",
    )
