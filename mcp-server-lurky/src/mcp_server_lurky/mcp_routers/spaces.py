"""
MCP-only endpoints for searching and parsing Twitter Spaces summaries.
"""

import logging
from typing import List

from fastapi import APIRouter, Depends, Query, HTTPException

from mcp_server_lurky.dependencies import get_lurky_client, get_db
from mcp_server_lurky.lurky.module import LurkyClient
from mcp_server_lurky.lurky.errors import LurkyAuthError, LurkyNotFoundError, LurkyAPIError
from mcp_server_lurky.schemas import SpaceDetailsSchema, SearchResponseSchema
from mcp_server_lurky.hybrid_routers.spaces import (
    perform_search_spaces,
    perform_get_space_details,
    perform_get_latest_summaries,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/search",
    tags=["Spaces"],
    operation_id="lurky_search_spaces_mcp",
    response_model=SearchResponseSchema,
)
async def lurky_search_spaces_mcp(
    q: str = Query(..., description="Search term for spaces"),
    limit: int = Query(10, ge=1, le=20),
    page: int = Query(0, ge=0),
    client: LurkyClient = Depends(get_lurky_client),
) -> SearchResponseSchema:
    """
    Search for Twitter Spaces discussions based on a keyword.
    MCP-only endpoint optimized for AI agents.
    """
    try:
        return await perform_search_spaces(q, limit, page, client)
    except LurkyAuthError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except LurkyAPIError as e:
        raise HTTPException(status_code=e.status_code or 500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/spaces/{space_id}",
    tags=["Spaces"],
    operation_id="lurky_get_space_details_mcp",
    response_model=SpaceDetailsSchema,
)
async def lurky_get_space_details_mcp(
    space_id: str,
    client: LurkyClient = Depends(get_lurky_client),
    db=Depends(get_db),
) -> SpaceDetailsSchema:
    """
    Get full details, summary, and segmented discussions for a specific Space ID.
    MCP-only endpoint optimized for AI agents.
    """
    try:
        return await perform_get_space_details(space_id, client, db)
    except LurkyAuthError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except LurkyNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"Space {space_id} not found: {e}")
    except LurkyAPIError as e:
        raise HTTPException(status_code=e.status_code or 500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/latest-summaries",
    tags=["Spaces"],
    operation_id="lurky_get_latest_summaries_mcp",
    response_model=List[SpaceDetailsSchema],
)
async def lurky_get_latest_summaries_mcp(
    topic: str = Query(..., description="Topic to fetch latest summaries for"),
    count: int = Query(3, ge=1, le=10),
    client: LurkyClient = Depends(get_lurky_client),
    db=Depends(get_db),
) -> List[SpaceDetailsSchema]:
    """
    Fetch the latest N unique Twitter Space summaries for a given topic.
    MCP-only endpoint optimized for AI agents.
    """
    try:
        return await perform_get_latest_summaries(topic, count, client, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except LurkyAuthError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except LurkyAPIError as e:
        raise HTTPException(status_code=e.status_code or 500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
