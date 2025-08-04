from __future__ import annotations

import argparse
import logging

import uvicorn
from fastapi import FastAPI
from mcp_server_youtube.logging_config import configure_logging, get_current_log_level
from mcp_server_youtube.routes import router
from mcp_server_youtube.server import app_lifespan
from mcp_server_youtube.server import mcp_server

# Configure logging first thing
configure_logging()


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
    logger.debug('Creating FastAPI application instance')

    # Create base app
    app = FastAPI(
        title='YouTube MCP Server',
        description='MCP Server for YouTube search and transcript functionality',
        version='1.0.0',
        lifespan=shared_lifespan,
    )

    # Include routes
    app.include_router(router)
    logger.debug('Routes registered successfully')

    return app


__all__ = ['create_app']


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run YouTube MCP server')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8000, help='Port to listen on')
    parser.add_argument('--reload', action='store_true', help='Enable hot reload')
    parser.add_argument('--log-level', help='Override log level (DEBUG/INFO/WARNING/ERROR)')

    args = parser.parse_args()

    # Override log level if specified
    if args.log_level:
        import os
        os.environ['LOG_LEVEL'] = args.log_level.upper()
        # Reconfigure logging with new level
        configure_logging()
    
    logger = logging.getLogger(__name__)

    current_level = get_current_log_level()
    logger.info(f'Starting YouTube MCP server on {args.host}:{args.port}')
    logger.info(f'Log level: {current_level}')
    logger.debug(f'Server configuration: host={args.host}, port={args.port}, reload={args.reload}')

    if args.reload:
        logger.warning('Hot reload is enabled - this should only be used in development')

    try:
        uvicorn.run(
            'mcp_server_youtube.__main__:create_app',
            factory=True,
            host=args.host,
            port=args.port,
            reload=args.reload,
            # Uvicorn's 'debug' mode is very noisy — we force 'info' to reduce log clutter,
            # even if our app-level log level is 'DEBUG'
            log_level=current_level.lower() if current_level != 'DEBUG' else 'info',  # Avoid uvicorn debug spam
        )
    except KeyboardInterrupt:
        logger.info('Server shutdown requested by user')
    except Exception as e:
        logger.error(f'Server startup failed: {str(e)}', exc_info=True)
        raise
    finally:
        logger.info('Server exited successfully')
