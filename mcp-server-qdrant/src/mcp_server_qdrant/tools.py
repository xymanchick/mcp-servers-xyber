"""
Core business logic for MCP Qdrant server tools.

This module contains the core logic for each tool separated from the MCP decorators 
to enable easier testing.
"""

import logging
from typing import Any

from fastmcp.exceptions import ToolError
from mcp_server_qdrant.exceptions import ValidationError
from mcp_server_qdrant.qdrant import Entry, QdrantConnector
from mcp_server_qdrant.schemas import QdrantFindRequest, QdrantGetCollectionInfoRequest, QdrantStoreRequest
from pydantic import ValidationError as PydanticValidationError
from qdrant_client.models import CollectionInfo, ScoredPoint

logger = logging.getLogger(__name__)


async def qdrant_store_logic(
    qdrant_connector: QdrantConnector,
    request: dict[str, Any],
) -> str:
    """Core logic for storing information in Qdrant."""
    try:
        validated_request = QdrantStoreRequest.model_validate(request)
        # Execute core logic
        entry = Entry(content=validated_request.information, metadata=validated_request.metadata)
        await qdrant_connector.store(entry, collection_name=validated_request.collection_name)

        logger.info(f"Successfully stored information in collection {validated_request.collection_name}")
        return f"Remembered: {validated_request.information} in collection {validated_request.collection_name}"

    except PydanticValidationError as ve:
        raise ValidationError(error=ve)

    except Exception as e:
        logger.error(f"Error storing information: {e}", exc_info=True)
        raise ToolError(f"Error storing information: {e}") from e


async def qdrant_find_logic(
    qdrant_connector: QdrantConnector,
    request: dict[str, Any],
) -> list[ScoredPoint] | str:
    """Core logic for finding information in Qdrant."""
    try:
        validated_request = QdrantFindRequest.model_validate(request)
        # Execute core logic
        search_results = await qdrant_connector.search(
            validated_request.query,
            collection_name=validated_request.collection_name,
            limit=validated_request.search_limit,
            filters=validated_request.filters,
        )

        # Format response
        if not search_results:
            message = f"No information found for the query '{validated_request.query}'"
            logger.info(message)
            return message

        logger.info(
            f"Successfully searched Qdrant with {len(search_results.points)} results"
        )
        return search_results.points

    except PydanticValidationError as ve:
        raise ValidationError(error=ve)

    except Exception as e:
        logger.error(f"Error searching Qdrant: {e}", exc_info=True)
        raise ToolError(f"Error searching Qdrant: {e}") from e


async def qdrant_get_collection_info_logic(
    qdrant_connector: QdrantConnector,
    request: dict[str, Any],
) -> CollectionInfo | dict[str, str]:
    """Core logic for getting collection information."""
    try:
        validated_request = QdrantGetCollectionInfoRequest.model_validate(request)

        collection_details = await qdrant_connector.get_collection_details(validated_request.collection_name)
        logger.info(f"Successfully retrieved details for collection {validated_request.collection_name}")
        return collection_details

    except PydanticValidationError as ve:
        raise ValidationError(error=ve)

    except Exception as e:
        collection_name = request.get("collection_name")

        logger.error(
            f"Error getting info for collection '{collection_name}': {e}", exc_info=True
        )
        # Return a structured error dict for the LLM rather than raising ToolError
        return {"error": f"Failed to get information for collection '{collection_name}': {str(e)}"}


async def qdrant_get_collections_logic(
    qdrant_connector: QdrantConnector,
) -> list[str]:
    """Core logic for getting all collection names."""
    try:
        collection_names = await qdrant_connector.get_collection_names()
        logger.info(f"Successfully retrieved {len(collection_names)} collection names")
        return collection_names

    except Exception as e:
        logger.error(f"Error getting collection names: {e}", exc_info=True)
        raise ToolError(f"Error getting collection names: {e}") from e
