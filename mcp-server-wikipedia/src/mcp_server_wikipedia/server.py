import logging
from collections.abc import AsyncIterator
from typing import Any, Dict, List
from contextlib import asynccontextmanager

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError

from mcp_server_wikipedia.wikipedia import (
    _WikipediaService,
    ArticleNotFoundError,
    WikipediaAPIError,
    WikipediaServiceError,
    get_wikipedia_service,
)

logger = logging.getLogger(__name__)

# --- Lifespan Management ---
@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[dict[str, Any]]:
    """Manage server startup/shutdown. Initializes the Wikipedia service."""
    logger.info("Lifespan: Initializing services...")
    try:
        wiki_service: _WikipediaService = get_wikipedia_service()
        logger.info("Lifespan: Wikipedia service initialized successfully")
        yield {"wiki_service": wiki_service}
    except WikipediaServiceError as init_err:
        logger.error(f"FATAL: Lifespan initialization failed: {init_err}", exc_info=True)
        raise init_err
    finally:
        logger.info("Lifespan: Shutdown cleanup completed")


# --- MCP Server Initialization ---
mcp_server = FastMCP(
    name="wikipedia",
    lifespan=app_lifespan,
)


def _get_service(ctx: Context) -> _WikipediaService:
    """Helper to get the wikipedia service from the context."""
    return ctx.request_context.lifespan_context["wiki_service"]


# --- Tool Definitions ---
@mcp_server.tool()
async def search_wikipedia(ctx: Context, query: str, limit: int = 10) -> List[str]:
    """Search Wikipedia for articles matching a query and return a list of titles."""
    try:
        results = await _get_service(ctx).search(query, limit=limit)
        return results
    except ValueError as e:
        raise ToolError(f"Input validation error: {e}") from e
    except WikipediaAPIError as e:
        raise ToolError(f"Wikipedia API error: {e}") from e


@mcp_server.tool()
async def get_article(ctx: Context, title: str) -> Dict[str, Any]:
    """Get the full content and metadata of a Wikipedia article by its exact title."""
    try:
        article = await _get_service(ctx).get_article(title)
        return article
    except ArticleNotFoundError as e:
        raise ToolError(str(e)) from e
    except WikipediaAPIError as e:
        raise ToolError(f"Wikipedia API error: {e}") from e


@mcp_server.tool()
async def get_summary(ctx: Context, title: str) -> str:
    """Get a summary of a Wikipedia article."""
    try:
        summary = await _get_service(ctx).get_summary(title)
        return summary
    except ArticleNotFoundError as e:
        raise ToolError(str(e)) from e
    except WikipediaAPIError as e:
        raise ToolError(f"Wikipedia API error: {e}") from e


@mcp_server.tool()
async def get_sections(ctx: Context, title: str) -> List[str]:
    """Get the section titles of a Wikipedia article."""
    try:
        sections = await _get_service(ctx).get_sections(title)
        return sections
    except ArticleNotFoundError as e:
        raise ToolError(str(e)) from e
    except WikipediaAPIError as e:
        raise ToolError(f"Wikipedia API error: {e}") from e


@mcp_server.tool()
async def get_links(ctx: Context, title: str) -> List[str]:
    """Get the links contained within a Wikipedia article."""
    try:
        links = await _get_service(ctx).get_links(title)
        return links
    except ArticleNotFoundError as e:
        raise ToolError(str(e)) from e
    except WikipediaAPIError as e:
        raise ToolError(f"Wikipedia API error: {e}") from e


@mcp_server.tool()
async def get_related_topics(
    ctx: Context, title: str, limit: int = 20
) -> List[str]:
    """Get topics related to a Wikipedia article based on its internal links."""
    try:
        topics = await _get_service(ctx).get_related_topics(title, limit)
        return topics
    except ArticleNotFoundError as e:
        raise ToolError(str(e)) from e
    except WikipediaAPIError as e:
        raise ToolError(f"Wikipedia API error: {e}") from e