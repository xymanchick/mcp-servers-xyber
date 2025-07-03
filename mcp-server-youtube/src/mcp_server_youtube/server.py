from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastmcp.exceptions import ToolError
from fastmcp.server import FastMCP
from mcp_server_youtube.routes import router
from mcp_server_youtube.youtube.models import YouTubeSearchRequest
from mcp_server_youtube.youtube.models import YouTubeSearchResponse
from mcp_server_youtube.youtube.models import YouTubeVideo
from mcp_server_youtube.youtube.module import get_youtube_searcher
from mcp_server_youtube.youtube.module import YouTubeSearcher
from mcp_server_youtube.youtube.youtube_errors import YouTubeClientError
from pydantic import ValidationError as PydanticValidationError
# from typing import TYPE_CHECKING


logger = logging.getLogger(__name__)


class ValidationError(ToolError):
    """Custom exception for input validation failures."""

    def __init__(self, message: str, code: str = 'VALIDATION_ERROR'):
        super().__init__(message, code=code)
        self.status_code = 400


# --- Lifespan Management --- #
@asynccontextmanager
async def app_lifespan(app: FastAPI) -> AsyncIterator[dict[str, object]]:
    """Manage application lifecycle events."""
    logger.info('Initializing YouTube services...')

    try:
        youtube_searcher: YouTubeSearcher = get_youtube_searcher()
        logger.info('Services initialized successfully')
        yield {'youtube_searcher': youtube_searcher}

    except YouTubeClientError as init_err:
        logger.error('Lifespan initialization failed', exc_info=True)
        raise ToolError(f'Service initialization failed: {init_err}') from init_err

    except Exception as unexpected_err:
        logger.error('Unexpected initialization error', exc_info=True)
        raise ToolError('Unexpected startup error') from unexpected_err

    finally:
        logger.info('Shutdown cleanup completed')


# Initialize FastAPI app with documentation
app = FastAPI(
    title='YouTube Search and Transcript API',
    description="""
    API for searching YouTube videos and retrieving their transcripts.

    This API allows you to:
    - Search YouTube videos using various filters
    - Retrieve video transcripts in multiple languages
    - Get video metadata including thumbnails and descriptions
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

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

# Initialize MCP server
mcp_server = FastMCP(
    lifespan=app_lifespan
)
# Add routes

app.include_router(router)


# --- Regular HTTP Endpoint --- #
@mcp_server.tool()
async def youtube_search_and_transcript(ctx, request):
    """Search YouTube videos and retrieve transcripts."""
    youtube_searcher = ctx.lifespan_context['youtube_searcher']

    try:
        validated_request = YouTubeSearchRequest(**request)
        search_result = await youtube_searcher.search_videos(
            query=validated_request.query,
            max_results=validated_request.max_results,
            language=validated_request.transcript_language or 'en'
        )

        response = YouTubeSearchResponse(
            results=[
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
            total_results=len(search_result)
        )

        return response.model_dump_json()

    except PydanticValidationError as ve:
        error_details = '; '.join(f"{err['loc'][0]}: {err['msg']}" for err in ve.errors())
        raise ValidationError(f'Invalid parameters: {error_details}')

    except YouTubeClientError as yt_err:
        raise ToolError(f'YouTube API error: {str(yt_err)}', code='YOUTUBE_API_ERROR')

    except Exception as e:
        raise ToolError(f'Internal error: {str(e)}', code='INTERNAL_ERROR')
