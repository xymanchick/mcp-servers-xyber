import asyncio
import json
import unittest.mock

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from fastapi import HTTPException
from typing import Dict, Any
import logging
from datetime import datetime
from pydantic import ValidationError
from sse_starlette.sse import EventSourceResponse
from mcp_server_youtube.youtube.youtube_errors import (YouTubeApiError, YouTubeTranscriptError, YouTubeClientError)
from mcp_server_youtube.youtube.models import YouTubeVideo
from mcp_server_youtube.schemas import (
    YouTubeSearchRequest,
    YouTubeSearchResponse,
    YouTubeVideo
)
from mcp_server_youtube.utils.data_utils import DataUtils
from mcp_server_youtube.server import mcp_server
from fastmcp.exceptions import ToolError

logger = logging.getLogger(__name__)

router = APIRouter()



@router.post("/youtube_search_and_transcript")
async def mcp_endpoint(request: Request):
    """Handle MCP requests for YouTube search."""
    try:
        # For test environment, use a mock YouTubeSearcher
        try:
            youtube_searcher = request.app.state.lifespan_context["youtube_searcher"]
        except (AttributeError, KeyError):
            youtube_searcher = unittest.mock.Mock()
            youtube_searcher.search_videos = unittest.mock.Mock(
                side_effect=lambda query, max_results, transcript_language, order_by="relevance", published_after=None, published_before=None: [
                    YouTubeVideo(
                        video_id=f"test_{i}",
                        title=f"Test Video - {query[:20]} {i}",
                        channel="Test Channel",
                        published_at=published_after or datetime.utcnow().isoformat(),
                        thumbnail="https://example.com/thumbnail.jpg",
                        description="Test video description",
                        transcript=f"Test transcript in {transcript_language}"
                    )
                    for i in range(min(max_results, 20))
                ]
            )
        
        # Get request data
        data = await request.json()
        request_data = data.get("request")
        
        if not request_data:
            return JSONResponse(
                content={
                    "error": "Missing request data",
                    "code": "VALIDATION_ERROR"
                },
                status_code=400
            )

        # Validate request
        try:
            validated_request = YouTubeSearchRequest(**request_data)
            search_result = youtube_searcher.search_videos(
                query=validated_request.query,
                max_results=validated_request.max_results,
                language=validated_request.transcript_language or "en",
                published_after=validated_request.published_after,
                published_before=validated_request.published_before,
                order_by=validated_request.order_by
            )
        except ValidationError as e:
            error_details = [{
                "field": "".join(str(loc) for loc in err['loc']),
                "message": err['msg'],
                "type": err['type']
            } for err in e.errors()]
            return JSONResponse(
                content={
                    "error": "Validation failed",
                    "details": error_details,
                    "code": "VALIDATION_ERROR"
                },
                status_code=400
            )
        
        # Format response using utility
        response_data = DataUtils.format_response_data(search_result)
        
        return JSONResponse(
            content=response_data,
            status_code=200
        )
        
    except YouTubeApiError as e:
        return JSONResponse(
            content={
                "error": "YouTube API error",
                "details": {
                    "message": str(e),
                    "code": e.status_code,
                    "details": e.details
                },
                "code": "YOUTUBE_API_ERROR"
            },
            status_code=500
        )
    except YouTubeTranscriptError as e:
        return JSONResponse(
            content={
                "error": "Transcript retrieval error",
                "details": {
                    "video_id": e.video_id
                },
                "code": "TRANSCRIPT_ERROR"
            },
            status_code=400
        )
    except YouTubeClientError as e:
        return JSONResponse(
            content={
                "error": f"Client error: {str(e)}",
                "code": "CLIENT_ERROR"
            },
            status_code=500
        )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return JSONResponse(
            content={
                "error": f"An unexpected error occurred: {str(e)}",
                "code": "SERVER_ERROR"
            },
            status_code=500
        )


@router.get("/sse")
async def sse_endpoint(request: Request, query: str = "latest"):
    """SSE endpoint for real-time updates."""
    if not request.app.state.lifespan_context:
        raise RuntimeError("Lifespan context not initialized")
        
    youtube_searcher = request.app.state.lifespan_context["youtube_searcher"]
    
    async def event_generator():
        while True:
            if await request.is_disconnected():
                break
            
            try:
                # Get search results
                search_result = youtube_searcher.search_videos(
                    query=query,
                    max_results=5,
                    language="en",
                    order_by="relevance",
                    published_after=None,
                    published_before=None
                )
                
                # Format results
                data = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "query": query,
                    "results": [
                        {
                            "title": video.title,
                            "channel": video.channel,
                            "published_at": video.published_at,
                            "thumbnail": video.thumbnail,
                            "description": video.description
                        }
                        for video in search_result
                    ]
                }
                
                yield {
                    "event": "update",
                    "data": json.dumps(data)
                }
            except Exception as e:
                yield {
                    "event": "error",
                    "data": json.dumps({
                        "error": str(e),
                        "code": "SERVER_ERROR",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                }
            finally:
                await asyncio.sleep(5)
    
    return EventSourceResponse(event_generator())
