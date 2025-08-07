"""Global exception handlers for the YouTube MCP server."""
from __future__ import annotations

import logging
from fastapi import Request
from fastapi.responses import JSONResponse
from mcp_server_youtube.youtube.youtube_errors import YouTubeClientError

logger = logging.getLogger(__name__)


async def youtube_exception_handler(request: Request, exc: YouTubeClientError) -> JSONResponse:
    """Handle structured YouTube exceptions with proper logging and response formatting.
    
    Args:
        request: The FastAPI request object
        exc: The YouTube client exception
        
    Returns:
        JSONResponse with structured error information
    """
    logger.error(
        f"{exc.code} | {exc.message} | Path: {request.url.path} | Method: {request.method}",
        extra={
            "error_code": exc.code,
            "status_code": exc.status_code,
            "path": str(request.url.path),
            "method": request.method,
            "user_agent": request.headers.get("user-agent"),
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_type": exc.code,
            "message": exc.message,
            "status_code": exc.status_code
        },
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions with proper logging and generic error response.
    
    Args:
        request: The FastAPI request object
        exc: The unhandled exception
        
    Returns:
        JSONResponse with generic error information
    """
    logger.exception(
        f"Unhandled error on {request.method} {request.url.path}: {exc}",
        extra={
            "path": str(request.url.path),
            "method": request.method,
            "error_type": type(exc).__name__,
            "user_agent": request.headers.get("user-agent"),
        }
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error_type": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred. Please try again later.",
            "status_code": 500
        }
    )