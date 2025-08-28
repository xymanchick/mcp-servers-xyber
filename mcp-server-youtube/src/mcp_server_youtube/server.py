from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastmcp.exceptions import ToolError
from fastmcp.server import FastMCP
from mcp_server_youtube.middleware import PerformanceMetricsMiddleware, get_metrics_response
from mcp_server_youtube.routes import router
from mcp_server_youtube.schemas import YouTubeSearchRequest
from mcp_server_youtube.youtube.models import YouTubeSearchResponse
from mcp_server_youtube.youtube.models import YouTubeVideo
from mcp_server_youtube.youtube.module import get_youtube_searcher
from mcp_server_youtube.youtube.module import YouTubeSearcher
from mcp_server_youtube.youtube.youtube_errors import YouTubeClientError, ValidationError as YouTubeValidationError
from mcp_server_youtube.utils.exception_handler import youtube_exception_handler, generic_exception_handler
from pydantic import ValidationError as PydanticValidationError


logger = logging.getLogger(__name__)


# --- Lifespan Management --- #
@asynccontextmanager
async def app_lifespan(app: FastAPI) -> AsyncIterator[dict[str, object]]:
    """Manage application lifecycle events."""
    logger.info('Starting YouTube MCP server initialization...')
    logger.debug('Checking environment configuration and API keys')

    try:
        youtube_searcher: YouTubeSearcher = get_youtube_searcher()
        logger.info('YouTube services initialized successfully')
        logger.debug(f'YouTube searcher configured with API key: {"✓ Present" if youtube_searcher.config.api_key else "✗ Missing"}')
        
        yield {'youtube_searcher': youtube_searcher}

    except YouTubeClientError as init_err:
        logger.error('YouTube service initialization failed', exc_info=True)
        logger.error(f'Configuration error details: {init_err}')
        raise ToolError(f'Service initialization failed: {init_err}') from init_err

    except Exception as unexpected_err:
        logger.error('Unexpected error during YouTube service initialization', exc_info=True)
        logger.debug(f'Unexpected error type: {type(unexpected_err).__name__}')
        raise ToolError('Unexpected startup error') from unexpected_err

    finally:
        logger.info('YouTube MCP server shutdown cleanup completed')
        logger.debug('All resources and connections cleaned up')


# Initialize FastAPI app with documentation
app = FastAPI(
    title='YouTube Search and Transcript API',
    description="""
    API for searching YouTube videos and retrieving their transcripts.

    This API allows you to:
    - Search YouTube videos using various filters
    - Retrieve video transcripts in multiple languages
    - Get video metadata including thumbnails and descriptions
    - Monitor performance metrics via /metrics endpoint
    """,
    version='1.0.0',
    contact={
        'name': 'Xyber Labs',
        'email': 'support@xyberlabs.com'
    },
    license_info={
        'name': 'Proprietary',
        'url': 'https://www.xyberlabs.com/license'
    }
)

# Add Performance Metrics Middleware (FIRST - to capture all requests)
app.add_middleware(PerformanceMetricsMiddleware, include_query_params=True)
logger.info('Performance metrics middleware added to FastAPI application')

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)
logger.debug('CORS middleware configured to allow all origins, methods, and headers')

# Add metrics endpoint
@app.get('/metrics')
async def metrics():
    """Prometheus metrics endpoint for monitoring and alerting."""
    return get_metrics_response()

# Add health check endpoint
@app.get('/health')
async def health():
    """Health check endpoint."""
    return {'status': 'healthy', 'service': 'youtube-mcp-server'}

# Initialize MCP server
mcp_server = FastMCP(
    lifespan=app_lifespan
)
# Add routes

app.include_router(router)
logger.debug('YouTube search routes included in the FastAPI application')

# Register global exception handlers
app.add_exception_handler(YouTubeClientError, youtube_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)
logger.info('Global exception handlers registered for structured error responses')


# --- Regular HTTP Endpoint --- #
@mcp_server.tool()
async def youtube_search_and_transcript(ctx, request: YouTubeSearchRequest):
    """Search YouTube videos and retrieve transcripts."""
    logger.debug(f'Received MCP tool request: {request}')
    youtube_searcher = ctx.lifespan_context['youtube_searcher']

    try:
        validated_request = request
        logger.debug(f'Request validated successfully: query="{validated_request.query}", max_results={validated_request.max_results}')
        
        search_result = await youtube_searcher.search_videos(
            query=validated_request.query,
            max_results=validated_request.max_results,
            language=validated_request.transcript_language or 'en'
        )

        response = YouTubeSearchResponse(
            videos=[
                YouTubeVideo(
                    video_id=video.video_id,
                    title=video.title,
                    channel=video.channel,
                    published_at=video.published_at,
                    thumbnail=video.thumbnail,
                    description=video.description,
                    transcript=video.transcript
                )
                for video in search_result
            ],
            total_results=len(search_result),
            next_page_token=search_result.next_page_token if hasattr(search_result, 'next_page_token') else None
        )

        logger.info(f'Successfully processed YouTube search request: {len(search_result)} videos found')
        logger.debug(f'Response prepared with {response.total_results} videos')
        return response.model_dump_json()

    except PydanticValidationError as ve:
        error_details = '; '.join(f"{err['loc'][0]}: {err['msg']}" for err in ve.errors())
        logger.warning(f'Request validation failed: {error_details}')
        logger.debug(f'Raw validation errors: {ve.errors()}')
        raise YouTubeValidationError(f'Invalid parameters: {error_details}')

    except YouTubeClientError as yt_err:
        logger.error(f'YouTube API error occurred: {str(yt_err)}', exc_info=True)
        raise ToolError(f'YouTube API error: {str(yt_err)}', code='YOUTUBE_API_ERROR')

    except Exception as e:
        logger.error(f'Unexpected error in youtube_search_and_transcript: {str(e)}', exc_info=True)
        logger.debug(f'Error type: {type(e).__name__}, Request: {request}')
        raise ToolError(f'Internal error: {str(e)}', code='INTERNAL_ERROR')
