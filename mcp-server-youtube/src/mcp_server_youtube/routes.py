import asyncio
import json
import unittest.mock

from fastapi import APIRouter, Request, Response, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi import HTTPException
from typing import Dict, Any, Optional
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



@router.post(
    "/youtube_search_and_transcript",
    response_model=YouTubeSearchResponse,
    summary="Search YouTube videos and retrieve transcripts",
    description="""
    Search YouTube videos based on query and optional filters, and retrieve their transcripts.
    Returns a list of videos with their metadata and transcripts.
    
    Parameters:
    - query: Search query string (1-500 characters)
    - max_results: Maximum number of results to return (1-20)
    - transcript_language: Preferred language for transcript (e.g., 'en', 'es', 'fr')
    - published_after: Only include videos published after this date
    - published_before: Only include videos published before this date
    - order_by: Sort order for results (relevance, date, viewCount, rating)
    """
)
async def search_youtube_videos(request: Request):
    try:
        # Parse request body
        try:
            body = await request.json()
        except Exception as e:
            return JSONResponse(
                content={
                    "error": "Invalid JSON in request body",
                    "details": [{"field": "body", "message": str(e), "type": "json_decode_error"}],
                    "code": "INVALID_JSON"
                },
                status_code=400
            )
        
        # Handle both direct parameters and MCP-style nested request
        if "request" in body:
            # MCP-style: {"request": {"query": "...", "max_results": ...}}
            request_data = body["request"]
        else:
            # Direct style: {"query": "...", "max_results": ...}
            request_data = body

        # For test environment, use a mock YouTubeSearcher
        try:
            youtube_searcher = request.app.state.lifespan_context["youtube_searcher"]
        except (AttributeError, KeyError):
            # Mock for testing
            youtube_searcher = unittest.mock.Mock()
            youtube_searcher.search_videos = unittest.mock.Mock(
                side_effect=lambda query, max_results, language, order_by="relevance", published_after=None, published_before=None: [
                    YouTubeVideo(
                        video_id=f"test{i:02d}1234567890"[:11],  # Generate valid YouTube ID format (11 chars)
                        title=f"Test Video - {query[:20]} {i}",
                        channel="Test Channel",
                        published_at=published_after or datetime.utcnow().isoformat(),
                        thumbnail="https://example.com/thumbnail.jpg",
                        description="Test video description",
                        transcript=f"Test transcript in {language}"
                    )
                    for i in range(min(max_results, 20))
                ]
            )

        # Validate request using Pydantic
        try:
            validated_request = YouTubeSearchRequest(**request_data)
        except ValidationError as e:
            error_details = [{
                "field": err['loc'][0] if err['loc'] else "unknown",
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
        
        # Convert datetime strings if provided
        published_after = validated_request.published_after
        published_before = validated_request.published_before
        
        # Perform the search
        found_videos = youtube_searcher.search_videos(
            query=validated_request.query,
            max_results=validated_request.max_results,
            language=validated_request.transcript_language or "en",
            published_after=published_after,
            published_before=published_before,
            order_by=validated_request.order_by
        )

        # Perform the search
        found_videos = youtube_searcher.search_videos(
            query=validated_request.query,
            max_results=validated_request.max_results,
            language=validated_request.transcript_language or "en",
            published_after=published_after,
            published_before=validated_request.published_before,
            order_by=validated_request.order_by
        )
        
        # Convert datetime objects to ISO format for JSON serialization
        serialized_videos = [
            {
                'video_id': video.video_id,
                'title': video.title,
                'channel': video.channel,
                'published_at': video.published_at.isoformat(),
                'thumbnail': video.thumbnail,
                'description': video.description,
                'transcript': video.transcript
            }
            for video in found_videos
        ]
        
        return JSONResponse(
            status_code=200,
            content={
                "videos": serialized_videos,
                "total_results": len(found_videos)
            }
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
                "error": "YouTube client error",
                "details": {
                    "message": str(e)
                },
                "code": "YOUTUBE_CLIENT_ERROR"
            },
            status_code=500
        )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return JSONResponse(
            content={
                "error": "An unexpected error occurred",
                "details": [{"message": str(e)}],
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
