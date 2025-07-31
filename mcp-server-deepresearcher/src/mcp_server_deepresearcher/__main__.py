import argparse
import logging
import os
import uvicorn
from fastapi import FastAPI

from mcp_server_deepresearcher.logging_config import configure_logging, LOGGING_LEVEL
from mcp_server_deepresearcher.server import mcp_server
from mcp_server_deepresearcher.deepresearcher.graph import DeepResearcher

configure_logging()
logger = logging.getLogger(__name__)

# --- Application Factory --- #
def create_app() -> FastAPI:
    """Create a FastAPI application to serve the MCP server."""
    mcp_app = mcp_server.http_app(path="/mcp", transport="streamable-http")
    
    app = FastAPI(
        title="Deep Researcher MCP Server",
        description="MCP server for conducting in-depth research on a topic.",
        version="0.1.0",
        lifespan=mcp_app.router.lifespan_context
    )   
    
    @app.get("/health", status_code=200)
    def health_check():
        return {"status": "ok"}
    
    app.mount("/mcp-server", mcp_app)
    return app

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Deep Researcher MCP server")
    parser.add_argument(
        "--host",
        default=os.getenv("MCP_DEEP_RESEARCHER_HOST", "0.0.0.0"),
        help="Host to bind to"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("MCP_DEEP_RESEARCHER_PORT", "8006")),
        help="Port to listen on"
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        default=os.getenv("DEEP_RESEARCHER_HOT_RELOAD", "false").lower() in ("true", "1", "t"),
        help="Enable hot reload"
    )

    args = parser.parse_args()
    logger.info(f"Starting Deep Researcher MCP server on {args.host}:{args.port}")

    uvicorn.run(
        "mcp_server_deep_researcher.__main__:create_app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=LOGGING_LEVEL.lower(),
        factory=True
    )