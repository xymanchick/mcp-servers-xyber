import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Optional

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from pydantic import BaseModel, Field, ValidationError as PydanticValidationError

from mcp_server_tavily.tavily import (
    TavilySearchResult,
    TavilyServiceError,
    _TavilyService,
    get_tavily_service,
)

logger = logging.getLogger(__name__)

# --- Custom Exceptions --- #
class ValidationError(ToolError):
    """Custom exception for input validation failures."""

    def __init__(self, message: str, code: str = "VALIDATION_ERROR"):
        self.message = message
        self.code = code
        self.status_code = 400
        super().__init__(message)



# --- Request Schema Definition --- #
class TavilySearchRequest(BaseModel):
    """Input schema for Tavily search tool."""

    query: str = Field(
        ...,
        min_length=1,
        max_length=512,
        description="The search query string for Tavily",
    )
    max_results: Optional[int] = Field(
        None,
        ge=1,
        le=50,
        description="Optional override for the maximum number of search results (min 1, max 50)",
    )



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
    query: str,  # The search query string for Tavily
    max_results: (
        int | None
    ) = None,  # Optional override for the maximum number of search results (min 1)
) -> str:
    """Performs a web search using the Tavily API based on the provided query."""
    tavily_service = ctx.request_context.lifespan_context["tavily_service"]

    try:
        # Validate input parameters
        TavilySearchRequest(
            query=query,
            max_results=max_results,
        )
        # Execute core logic
        search_results: list[TavilySearchResult] = await tavily_service.search(
            query=query, max_results=max_results
        )

        # Format response
        formatted_response = "\n\n".join([str(result) for result in search_results])
        logger.info(
            f"Successfully processed search request with {len(search_results)} results"
        )

        return formatted_response

   

    except PydanticValidationError as ve:
        error_details = "\n".join(
            f"  - {'.'.join(str(loc).capitalize() for loc in err['loc'])}: {err['msg']}"
            for err in ve.errors()
        )
        raise ValidationError(f"Invalid parameters:\n{error_details}")
    
    except ValueError as val_err:
        logger.warning(f"Input validation error: {val_err}")
        raise ToolError(f"Input validation error: {val_err}") from val_err

    except TavilyServiceError as service_err:
        logger.error(f"Tavily service error: {service_err}", exc_info=True)
        raise ToolError(f"Tavily service error: {service_err}") from service_err

    except Exception as e:
        logger.error(f"Unexpected error during search: {e}", exc_info=True)
        raise ToolError("An unexpected error occurred during search.") from e
