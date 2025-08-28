# This template file mostly will stay the same for all MCP servers
# It is responsible for launching a uvicorn server with the given MCP server

import argparse
import logging
import os

import uvicorn
from fastapi import FastAPI
from mcp_server_twitter.logging_config import configure_logging, logging_level
from mcp_server_twitter.server import mcp_server

# Configure enhanced logging before any other imports
configure_logging()
logger = logging.getLogger(__name__)

# --- Application Factory --- #


def create_app() -> FastAPI:
    """Create a FastAPI application that can serve the provided mcp server with SSE."""
    # Create the MCP ASGI app
    mcp_app = mcp_server.http_app(path="/mcp", transport="streamable-http")

    # Create FastAPI app with proper FastMCP lifespan
    app = FastAPI(
        title="Twitter MCP Server",
        description="MCP server for Twitter integration",
        version="1.0.0",
        lifespan=mcp_app.lifespan,
    )

    # Mount MCP server
    app.mount("/mcp-server", mcp_app)

    return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Twitter MCP server")
    parser.add_argument(
        "--host",
        default=os.getenv("MCP_TWITTER_HOST", "0.0.0.0"),
        help="Host to bind to (Default: MCP_TWITTER_HOST or 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("MCP_TWITTER_PORT", "8000")),
        help="Port to listen on (Default: MCP_TWITTER_PORT or 8000)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        default=os.getenv("TWITTER_HOT_RELOAD", "false").lower()
        in ("true", "1", "t", "yes"),
        help="Enable hot reload (env: TWITTER_HOT_RELOAD)",
    )
    parser.add_argument(
        "--log-level",
        default=os.getenv("LOG_LEVEL", "INFO").upper(),
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set logging level (env: LOG_LEVEL)",
    )

    args = parser.parse_args()
    
    # Update log level if provided via command line
    if args.log_level != os.getenv("LOG_LEVEL", "INFO").upper():
        os.environ["LOG_LEVEL"] = args.log_level
        # Reconfigure logging with new level
        configure_logging()
        logger = logging.getLogger(__name__)
    
    logger.info(f"Starting Twitter MCP server on {args.host}:{args.port}")

    uvicorn.run(
        "mcp_server_twitter.__main__:create_app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=logging_level.lower(),
        factory=True,
    )