import argparse
import logging
import os

import uvicorn
from fastapi import FastAPI

from mcp_server_stability.logging_config import configure_logging, logging_level
from mcp_server_stability.server import mcp_server

configure_logging()
logger = logging.getLogger(__name__)

# --- Application Factory --- #


def create_app() -> FastAPI:
    """Create a FastAPI application that can serve the provided MCP server with SSE."""
    # Create the MCP ASGI app
    mcp_app = mcp_server.http_app(path="/mcp", transport="streamable-http")

    # Create FastAPI app
    app = FastAPI(
        title="Stable Diffusion MCP Server",
        description="MCP server with stable diffusion image generation functionality",
        version="1.0.0",
        lifespan=mcp_app.router.lifespan_context,
    )
    # Mount MCP server

    app.mount("/mcp-server", mcp_app)

    return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Stable Diffusion MCP server")
    parser.add_argument(
        "--host",
        default=os.getenv("MCP_STABLE_DIFFUSION_HOST", "0.0.0.0"),
        help="Host to bind to (Default: MCP_STABLE_DIFFUSION_HOST or 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("MCP_STABLE_DIFFUSION_PORT", "8000")),
        help="Port to listen on (Default: MCP_STABLE_DIFFUSION_PORT or 8000)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        default=os.getenv("MCP_STABLE_DIFFUSION_HOT_RELOAD", "false").lower()
        in ("true", "1", "t", "yes"),
        help="Enable hot reload (env: MCP_STABLE_DIFFUSION_HOT_RELOAD)",
    )

    args = parser.parse_args()
    logger.info(f"Starting Stable Diffusion MCP server on {args.host}:{args.port}")

    uvicorn.run(
        "mcp_server_stability.__main__:create_app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=logging_level.lower(),
        factory=True,
    )
