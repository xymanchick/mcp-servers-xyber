import logging
from contextlib import asynccontextmanager

from typing import AsyncIterator, Any, Literal
from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError

from mcp_server_youtube.youtube import (YouTubeClientError, YouTubeSearcher,
                                        get_youtube_searcher)

logger = logging.getLogger(__name__)





# --- Lifespan Management --- #
@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[dict[str, Any]]:
    """Manage server startup/shutdown. Initializes the YouTube service."""
    logger.info("Lifespan: Initializing services...")
    
    try:
        # Initialize services
        youtube_searcher: YouTubeSearcher = get_youtube_searcher()
        
        logger.info("Lifespan: Services initialized successfully")
        yield {"youtube_searcher": youtube_searcher}
    
    except YouTubeClientError as init_err:
        logger.error(f"FATAL: Lifespan initialization failed: {init_err}", exc_info=True)
        raise init_err
    
    except Exception as startup_err:
        logger.error(f"FATAL: Unexpected error during lifespan initialization: {startup_err}", exc_info=True)
        raise startup_err
    
    finally:
        logger.info("Lifespan: Shutdown cleanup completed")


# --- MCP Server Initialization --- #
mcp_server = FastMCP(
    name="youtube",
    lifespan=app_lifespan
)


# --- Tool Definitions --- #
@mcp_server.tool()
async def youtube_search_and_transcript(
    ctx: Context,
    query: str,  # The search query string for YouTube videos
    max_results: int = 3,  # Maximum number of video results to return (1-20)
    transcript_language: str = "en",  # The language code for the transcript (e.g., 'en', 'es')
) -> str:
    """Searches YouTube for videos based on a query and attempts to retrieve the transcript for ALL videos found (limited to max_results). Useful for getting information or content from YouTube videos."""
    youtube_searcher = ctx.request_context.lifespan_context["youtube_searcher"]

    try:
        # Execute core logic
        logger.debug(f"Searching YouTube for: '{query}'")
        search_result = youtube_searcher.search_videos(
            query=query,
            max_results=max_results,
            language=transcript_language,
        )
        
        logger.debug(f"Found {len(search_result)} videos")
        formatted_result = ",\n\n".join([str(video) for video in search_result])
        
        return formatted_result
    
    except YouTubeClientError as yt_err:
        logger.error(f"YouTube client error: {yt_err}", exc_info=True)
        raise ToolError(f"YouTube client error: {yt_err}") from yt_err
    
    except Exception as e:
        logger.error(f"Unexpected error during search: {e}", exc_info=True)
        raise ToolError("An unexpected error occurred during search.") from e
