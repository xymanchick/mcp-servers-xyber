import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pydantic import ValidationError as PydanticValidationError
from typing import Any

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from mcp_server_arxiv.arxiv import (
    ArxivApiError,
    ArxivConfigError,
    ArxivSearchResult,
    ArxivServiceError,
    _ArxivService,
    get_arxiv_service,
)
from mcp_server_arxiv.schemas import ArxivSearchRequest

logger = logging.getLogger(__name__)



# --- Custom Exceptions --- #
class ValidationError(ToolError):
    """Custom exception for input validation failures."""

    def __init__(self, message: str, code: str = "VALIDATION_ERROR"):
        self.message = message
        self.code = code
        self.status_code = 400
        super().__init__(message)

# --- Lifespan Management --- #
@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[dict[str, Any]]:
    """Manage server startup/shutdown. Initializes the ArXiv service."""
    logger.info("Lifespan: Initializing services...")

    try:
        # Initialize services
        arxiv_service: _ArxivService = get_arxiv_service()

        logger.info("Lifespan: Services initialized successfully")
        yield {"arxiv_service": arxiv_service}

    except (ArxivConfigError, ArxivServiceError) as init_err:
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
mcp_server = FastMCP(name="arxiv", lifespan=app_lifespan)


# --- Tool Definitions --- #
@mcp_server.tool()
async def arxiv_search(
    ctx: Context,
    request: ArxivSearchRequest,
) -> str:
    """Searches arXiv for scientific papers based on a query, downloads PDFs, extracts text, and returns formatted results."""
    arxiv_service = ctx.request_context.lifespan_context["arxiv_service"]

    try:
        
        # Execute core logic
        search_results: list[ArxivSearchResult] = await arxiv_service.search(
            query=request.query,
            max_results_override=request.max_results,
            max_text_length_override=request.max_text_length,
        )

        # Format response
        if not search_results:
            logger.info(
                "No relevant papers found or processed on arXiv for the given query"
            )
            return "No relevant papers found or processed on arXiv for the given query"

        formatted_items = ["ArXiv Search Results:\n"]
        for i, result in enumerate(search_results):
            formatted_items.append(f"\n--- Paper {i + 1} ---\n{str(result)}")

        formatted_response = "\n".join(formatted_items)
        logger.info(
            f"Successfully processed search request. Returning {len(search_results)} formatted ArXiv results"
        )

        return formatted_response

    
    except PydanticValidationError as ve:
        error_details = "\n".join(
            f"  - {'.'.join(str(loc).capitalize() for loc in err['loc'])}: {err['msg']}"
            for err in ve.errors()
        )
        raise ValidationError(f"Invalid parameters:\n{error_details}")

    except ArxivApiError as api_err:
        logger.error(f"ArXiv API error: {api_err}", exc_info=True)
        raise ToolError(f"ArXiv API error: {api_err}") from api_err

    except ArxivServiceError as service_err:
        logger.error(f"ArXiv service error: {service_err}", exc_info=True)
        raise ToolError(f"ArXiv service error: {service_err}") from service_err

    except Exception as e:
        logger.error(f"Unexpected error during search: {e}", exc_info=True)
        raise ToolError("An unexpected error occurred during search.") from e
