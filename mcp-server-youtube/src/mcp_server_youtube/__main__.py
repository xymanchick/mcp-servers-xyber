from __future__ import annotations

import argparse
import logging

import uvicorn
from fastapi import FastAPI
from mcp_server_youtube.logging_config import configure_logging
from mcp_server_youtube.routes import router
from mcp_server_youtube.server import app_lifespan, mcp_server

configure_logging()
logger = logging.getLogger(__name__)


class State:
    """Shared application state."""

    def __init__(self):
        self.lifespan_context = None


async def shared_lifespan(app: FastAPI):
    async with app_lifespan(app) as lifespan_context:
        app.state.lifespan_context = lifespan_context
        yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="YouTube MCP Server",
        description="Server for YouTube search and transcript retrieval",
        version="1.0.0",
        lifespan=shared_lifespan,
    )

    # Mount MCP server
    app.mount("/mcp", mcp_server.http_app())

    # Include routes
    app.include_router(router)

    return app


__all__ = ["create_app"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run YouTube MCP server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on")
    parser.add_argument("--reload", action="store_true", help="Enable hot reload")

    args = parser.parse_args()

    uvicorn.run(
        "mcp_server_youtube.__main__:create_app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        factory=True,
    )
