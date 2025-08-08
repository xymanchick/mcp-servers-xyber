import argparse
import logging
import os

import uvicorn
from fastapi import FastAPI

from mcp_server_telegram_parser.logging_config import LOGGING_LEVEL as logging_level
from mcp_server_telegram_parser.logging_config import configure_logging
from mcp_server_telegram_parser.server import mcp_server

configure_logging()
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    mcp_app = mcp_server.http_app(path="/mcp", transport="streamable-http")
    app = FastAPI(
        title="Telegram Parser MCP Server",
        description="Parses public Telegram channels via Telethon",
        version="1.0.0",
        lifespan=mcp_app.router.lifespan_context,
    )

    @app.get("/health", status_code=200)
    def health_check():
        return {"status": "ok"}

    app.mount("/mcp-server", mcp_app)
    return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Telegram Parser MCP server")
    parser.add_argument(
        "--host",
        default=os.getenv("MCP_TELEGRAM_PARSER_HOST", "0.0.0.0"),
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("MCP_TELEGRAM_PARSER_PORT", "8012")),
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        default=os.getenv("MCP_TELEGRAM_PARSER_RELOAD", "false").lower() in ("true", "1", "t", "yes"),
    )

    args = parser.parse_args()
    logger.info(f"Starting Telegram Parser MCP server on {args.host}:{args.port}")

    uvicorn.run(
        "mcp_server_telegram_parser.__main__:create_app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=logging_level.lower(),
        factory=True,
    )


