import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Optional

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError

from mcp_server_tavily.tavily import (
    TavilySearchResult,
    TavilyServiceError,
    _TavilyService,
    get_tavily_service,
)
from mcp_server_tavily.schemas import TavilySearchRequest

logger = logging.getLogger(__name__)



# --- Lifespan Management --- #
@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[dict[str, Any]]:
    """Manage server startup/shutdown. Initializes the Tavily service."""
    logger.info("Lifespan: Initializing services...")

    try:
        # Initialize services
        tavily_service: _TavilyService = get_tavily_service()

        logger.info("Lifespan: Services initialized successfully")
        yield {"tavily_service": tavily_service}

    except TavilyServiceError as init_err:
        logger.error(
            f"FATAL: Lifespan initialization failed: {init_err}", exc_info=True
        )
        raise init_err

    except Exception as startup_err:
        logger.error(
            f"FATAL: Unexpected error during lifespan initialization: {startup_err}",
            exc_info=True,
        )
        raise startup_err

    finally:
        logger.info("Lifespan: Shutdown cleanup completed")


# --- MCP Server Initialization --- #
mcp_server = FastMCP(name="tavily", lifespan=app_lifespan)


# --- Tool Definitions --- #
@mcp_server.tool()
async def tavily_web_search(
    ctx: Context,
    request: TavilySearchRequest,
) -> str:
    """Performs a web search using the Tavily API based on the provided query."""
    tavily_service = ctx.request_context.lifespan_context["tavily_service"]

    try:
        # Execute core logic using the validated request data
        search_results: list[TavilySearchResult] = await tavily_service.search(
            query=request.query, max_results=request.max_results
        )

        # Format response
        formatted_response = "\n\n".join([str(result) for result in search_results])
        logger.info(
            f"Successfully processed search request with {len(search_results)} results"
        )

        return formatted_response

    except ValueError as val_err:
        logger.warning(f"Input validation error: {val_err}")
        raise ToolError(f"Input validation error: {val_err}") from val_err

    except TavilyServiceError as service_err:
        logger.error(f"Tavily service error: {service_err}", exc_info=True)
        raise ToolError(f"Tavily service error: {service_err}") from service_err

    except Exception as e:
        logger.error(f"Unexpected error during search: {e}", exc_info=True)
        raise ToolError("An unexpected error occurred during search.") from e
