import argparse
import logging
import os

import uvicorn
from fastapi import FastAPI

from mcp_server_hangman.logging_config import LOGGING_LEVEL as logging_level
from mcp_server_hangman.logging_config import configure_logging
from mcp_server_hangman.server import mcp_server


configure_logging()
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    mcp_app = mcp_server.http_app(path="/mcp", transport="streamable-http")
    app = FastAPI(
        title="Hangman MCP Server",
        description="Play Hangman through MCP tools",
        version="1.0.0",
        lifespan=mcp_app.router.lifespan_context,
    )

    @app.get("/health", status_code=200)
    def health_check():
        return {"status": "ok"}

    app.mount("/mcp-server", mcp_app)
    return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Hangman MCP server")
    parser.add_argument(
        "--host",
        default=os.getenv("MCP_HANGMAN_HOST", "0.0.0.0"),
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("MCP_HANGMAN_PORT", "8015")),
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        default=os.getenv("MCP_HANGMAN_RELOAD", "false").lower() in ("true", "1", "t", "yes"),
    )

    args = parser.parse_args()
    logger.info(f"Starting Hangman MCP server on {args.host}:{args.port}")

    uvicorn.run(
        "mcp_server_hangman.__main__:create_app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=logging_level.lower(),
        factory=True,
    )


