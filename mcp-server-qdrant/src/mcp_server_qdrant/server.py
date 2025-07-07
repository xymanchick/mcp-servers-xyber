"""
MCP server implementation for Qdrant vector database.
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from enum import StrEnum
from typing import Any

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from pydantic import BaseModel, Field
from qdrant_client.models import CollectionInfo, ScoredPoint

from mcp_server_qdrant.qdrant import Entry, QdrantConnector, get_qdrant_connector

logger = logging.getLogger(__name__)

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


# --- Tool Name Enums --- #


class ToolNames(StrEnum):
    QDRANT_STORE = "qdrant-store"
    QDRANT_FIND = "qdrant-find"


# --- Lifespan Management for MCP Server --- #


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[dict[str, Any]]:
    """Manage server startup/shutdown. Initializes Qdrant services."""
    logger.info("Lifespan: Initializing services...")

    try:
        # Initialize services
        qdrant_connector: QdrantConnector = get_qdrant_connector()

        logger.info("Lifespan: Services initialized successfully")
        yield {"qdrant_connector": qdrant_connector}

    except Exception as init_err:
        logger.error(
            f"FATAL: Lifespan initialization failed: {init_err}", exc_info=True
        )
        raise init_err

    finally:
        logger.info("Lifespan: Shutdown cleanup completed")


# --- MCP Server Initialization --- #
mcp_server = FastMCP(name="qdrant", lifespan=app_lifespan)

# --- Tool Definitions --- #


@mcp_server.tool()
async def qdrant_store(
    ctx: Context,
    information: str,  # The information to store
    collection_name: str,  # The name of the collection to store the information in
    metadata: dict[str, Any]
    | None = None,  # JSON metadata to store with the information, optional
) -> str:
    """
    Keep the memory for later use, when you are asked to remember something.
    The collection will be created automatically with configured settings if it doesn't exist.
    """
    qdrant_connector = ctx.request_context.lifespan_context["qdrant_connector"]

    try:
        # Execute core logic
        entry = Entry(content=information, metadata=metadata)
        await qdrant_connector.store(entry, collection_name=collection_name)

        logger.info(f"Successfully stored information in collection {collection_name}")
        return f"Remembered: {information} in collection {collection_name}"

    except Exception as e:
        logger.error(f"Error storing information: {e}", exc_info=True)
        raise ToolError(f"Error storing information: {e}") from e


@mcp_server.tool()
async def qdrant_find(
    ctx: Context,
    query: str,  # The query to use for the search
    collection_name: str,  # The name of the collection to search in
    search_limit: int = 10,  # The maximum number of results to return
    filters: dict[str, Any]
    | None = None,  # Optional filters as field_path -> value pairs
) -> list[ScoredPoint] | str:
    """
    Look up memories in Qdrant. Use this tool when you need to find memories by their content.
    You can optionally filter by metadata fields (e.g., {"metadata.user_id": "alice", "metadata.category": "work"}).
    Filtering by tenant fields (if configured) will be much faster than filtering by other fields.
    """
    qdrant_connector = ctx.request_context.lifespan_context["qdrant_connector"]

    try:
        # Execute core logic
        search_results = await qdrant_connector.search(
            query, collection_name=collection_name, limit=search_limit, filters=filters
        )

        # Format response
        if not search_results:
            logger.info(f"No information found for the query '{query}'")
            return f"No information found for the query '{query}'"

        logger.info(
            f"Successfully searched Qdrant with {len(search_results.points)} results"
        )
        return search_results.points

    except Exception as e:
        logger.error(f"Error searching Qdrant: {e}", exc_info=True)
        raise ToolError(f"Error searching Qdrant: {e}") from e


@mcp_server.tool()
async def qdrant_get_collection_info(
    ctx: Context,
    collection_name: str,  # The name of the collection to get information about
) -> CollectionInfo:
    """
    Retrieves detailed configuration and schema information for a specific Qdrant collection.
    Use this to understand how a collection is set up, what fields are indexed,
    if it's configured for multi-tenancy, and its vector parameters.
    """
    qdrant_connector = ctx.request_context.lifespan_context["qdrant_connector"]

    try:
        collection_details = await qdrant_connector.get_collection_details(
            collection_name
        )
        logger.info(f"Successfully retrieved details for collection {collection_name}")
        return collection_details
    except Exception as e:
        logger.error(
            f"Error getting info for collection '{collection_name}': {e}", exc_info=True
        )
        # Return a structured error dict for the LLM rather than raising ToolError
        return {
            "error": f"Failed to get information for collection '{collection_name}': {str(e)}"
        }


@mcp_server.tool()
async def qdrant_get_collections(
    ctx: Context,
) -> list[str]:
    """
    Retrieves the names of all collections in the Qdrant database.
    Use this to discover what collections are available before storing or searching data.
    """
    qdrant_connector = ctx.request_context.lifespan_context["qdrant_connector"]

    try:
        collection_names = await qdrant_connector.get_collection_names()
        logger.info(f"Successfully retrieved {len(collection_names)} collection names")
        return collection_names
    except Exception as e:
        logger.error(f"Error getting collection names: {e}", exc_info=True)
        raise ToolError(f"Error getting collection names: {e}") from e
