# This template file mostly will stay the same for all MCP servers
# It is responsible for launching a uvicorn server with the given MCP server

import argparse
import logging
import os

import uvicorn
from fastapi import FastAPI

from mcp_server_calculator.logging_config import configure_logging, logging_level
from mcp_server_calculator.server import mcp_server

configure_logging()
logger = logging.getLogger(__name__)

# --- Application Factory --- #


def create_app() -> FastAPI:
    """Create a FastAPI application that can server the provied mcp server with SSE."""
    # Create the MCP ASGI app
    mcp_app = mcp_server.http_app(path="/mcp", transport="streamable-http")

    # Create FastAPI app
    app = FastAPI(
        title="Calculator MCP Server",
        description="MCP server with calculator functionality",
        version="1.0.0",
        lifespan=mcp_app.router.lifespan_context,
    )
    # Mount MCP server

    app.mount("/mcp-server", mcp_app)

    return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Calculator MCP server")
    parser.add_argument(
        "--host",
        default=os.getenv(
            "MCP_CALCULATOR_HOST", "0.0.0.0"
        ),  # Override with your env variables
        help="Host to bind to (Default: MCP_CALCULATOR_HOST or 0.0.0.0)",  # Override with your env variables
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(
            os.getenv("MCP_CALCULATOR_PORT", "8000")
        ),  # Override with your env variables
        help="Port to listen on (Default: MCP_CALCULATOR_PORT or 8000)",  # Override with your env variables
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        default=os.getenv("MCP_CALCULATOR_HOT_RELOAD", "false").lower()
        in ("true", "1", "t", "yes"),  # Override with your env variables
        help="Enable hot reload (env: MCP_CALCULATOR_HOT_RELOAD)",  # Override with your env variables
    )

    args = parser.parse_args()
    logger.info(f"Starting Calculator MCP server on {args.host}:{args.port}")

    # Don't forget to change the module name to your own!
    uvicorn.run(
        "mcp_server_calculator.__main__:create_app",  # This is required when using debugpy
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=logging_level.lower(),
        factory=True,  # This is required when using debugpy
    )
