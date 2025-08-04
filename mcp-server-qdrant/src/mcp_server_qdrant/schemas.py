from typing import Any
from pydantic import BaseModel, Field

# --- Tool Input/Output Schemas --- #


class QdrantStoreRequest(BaseModel):
    """Input schema for the qdrant-store tool."""

    information: str = Field(..., description="The information to store.")
    collection_name: str = Field(
        ..., description="The name of the collection to store the information in."
    )
    metadata: dict[str, Any] | None = Field(
        None, description="JSON metadata to store with the information, optional."
    )


class QdrantFindRequest(BaseModel):
    """Input schema for the qdrant-find tool."""

    query: str = Field(..., description="The query to use for the search.")
    collection_name: str = Field(
        ..., description="The name of the collection to search in."
    )
    search_limit: int = Field(
        10, description="The maximum number of results to return."
    )


class QdrantGetCollectionRequest(BaseModel):
    """Input schema for the qdrant-find by name tool."""

    collection_name: str = Field(
        ..., description="The name of the collection to search in."
    )
