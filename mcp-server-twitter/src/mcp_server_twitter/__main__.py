import argparse
import logging
import os

import uvicorn
from mcp_server_twitter.logging_config import configure_logging, logging_level
from mcp_server_twitter.app import create_app

configure_logging()
logger = logging.getLogger(__name__)


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
        type=lambda v: v.lower() in ("true", "1", "t", "yes"),
        default=os.getenv("TWITTER_HOT_RELOAD", "false").lower()
        in ("true", "1", "t", "yes"),
        help="Enable hot reload (env: TWITTER_HOT_RELOAD)",
    )
    parser.add_argument(
        "--logging-level",
        default=os.getenv("LOGGING_LEVEL", "INFO").upper(),
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set logging level (env: LOGGING_LEVEL)",
    )

    args = parser.parse_args()
    
    if args.logging_level != os.getenv("LOGGING_LEVEL", "INFO").upper():
        os.environ["LOGGING_LEVEL"] = args.logging_level
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