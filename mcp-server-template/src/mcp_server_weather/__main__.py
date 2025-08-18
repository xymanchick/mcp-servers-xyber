# This template file mostly will stay the same for all MCP servers
# It is responsible for launching a uvicorn server with the given MCP server

import argparse
import logging
import os

import uvicorn
from fastapi import FastAPI
from mcp_server_weather.logging_config import configure_logging, logging_level
from mcp_server_weather.server import mcp_server

# Configure logging first thing
configure_logging()
logger = logging.getLogger(__name__)


# --- Application Factory --- #
def create_app() -> FastAPI:
    """Create a FastAPI application that serves the MCP server with streamable-http

    Returns:
        Configured FastAPI application
    """
    # Create the MCP ASGI app
    mcp_app = mcp_server.http_app(path="/mcp", transport="streamable-http")

    # Create FastAPI app
    app = FastAPI(
        title="Weather MCP Server",
        description="MCP server providing weather information from OpenWeatherMap API",
        version="0.1.0",
        lifespan=mcp_app.router.lifespan_context,
    )

    # Mount MCP server
    app.mount("/mcp-server", mcp_app)

    return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Weather MCP server")
    parser.add_argument(
        "--host",
        default=os.getenv("MCP_WEATHER_HOST", "0.0.0.0"),
        help="Host to bind to (Default: MCP_WEATHER_HOST or 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("MCP_WEATHER_PORT", "8000")),
        help="Port to listen on (Default: MCP_WEATHER_PORT or 8000)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        default=os.getenv("MCP_WEATHER_HOT_RELOAD", "false").lower()
        in ("true", "1", "t", "yes"),
        help="Enable hot reload (env: MCP_WEATHER_HOT_RELOAD)",
    )

    args = parser.parse_args()
    logger.info(f"Starting Weather MCP server on {args.host}:{args.port}")

    uvicorn.run(
        "mcp_server_weather.__main__:create_app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=logging_level.lower(),
        factory=True,  # This is required when using debugpy
    )
