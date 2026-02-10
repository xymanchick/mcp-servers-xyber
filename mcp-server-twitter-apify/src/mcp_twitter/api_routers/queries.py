"""
This module implements REST-only endpoints for query management.

Main responsibility: Provide endpoints for listing query types and queries that are only available via REST API.
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from mcp_twitter.dependencies import get_registry, get_scraper
from mcp_twitter.twitter import QueryRegistry, QueryType, TwitterScraper
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()


class QueryTypeInfo(BaseModel):
    """Query type information."""

    type: QueryType
    description: str
    example: str
    preset_count: int


class QueryInfo(BaseModel):
    """Query information."""

    id: str
    type: QueryType
    name: str


@router.get(
    "/v1/types",
    tags=["Queries"],
    operation_id="list_types",
    response_model=list[QueryTypeInfo],
)
async def list_types(
    registry: QueryRegistry = Depends(get_registry),
) -> list[QueryTypeInfo]:
    """List all available query types with descriptions."""
    descriptions: dict[str, str] = {
        "topic": "Search tweets by keyword/topic (supports sort Top/Latest, verified/image filters)",
        "profile": "Search tweets from a specific username (supports date range filters)",
        "replies": "Fetch replies for a thread via conversation_id",
    }
    examples: dict[str, str] = {
        "topic": 'POST /hybrid/v1/search/topic {"topic": "starlink", "sort": "Top", "max_items": 10}',
        "profile": 'POST /hybrid/v1/search/profile {"username": "elonmusk", "max_items": 100}',
        "replies": 'POST /hybrid/v1/search/replies {"conversation_id": "1728108619189874825"}',
    }

    return [
        QueryTypeInfo(
            type=q_type,
            description=descriptions.get(q_type, ""),
            example=examples.get(q_type, ""),
            preset_count=len(registry.by_type(q_type)),
        )
        for q_type in registry.types()
    ]


@router.get(
    "/v1/queries",
    tags=["Queries"],
    operation_id="list_queries",
    response_model=list[QueryInfo],
)
async def list_queries(
    registry: QueryRegistry = Depends(get_registry),
    query_type: QueryType | None = Query(None, description="Filter by query type"),
) -> list[QueryInfo]:
    """List all available queries, optionally filtered by type."""
    queries = registry.list_queries(query_type=query_type)
    return [QueryInfo(id=q.id, type=q.type, name=q.name) for q in queries]


@router.get(
    "/v1/results/{filename}",
    tags=["Queries"],
    operation_id="get_results",
)
async def get_results(filename: str) -> dict[str, str]:
    """
    Get saved search results by query key (deprecated: use search endpoints directly).

    This endpoint is kept for backward compatibility but results are now stored in DB.
    """
    raise HTTPException(
        status_code=410,
        detail="File-based results are deprecated. Use search endpoints directly to access cached results.",
    )


@router.get(
    "/v1/results",
    tags=["Queries"],
    operation_id="list_results",
)
async def list_results(
    scraper: TwitterScraper = Depends(get_scraper),
) -> dict[str, str | bool]:
    """
    List cache status (deprecated: file listing no longer supported).

    Results are now stored in Postgres database cache.
    """
    return {
        "message": "File-based results are deprecated. Results are cached in Postgres database.",
        "cache_enabled": scraper.use_cache if scraper else False,
    }
