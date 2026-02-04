"""
Main application factory for the Telegram MCP Server.

Main responsibility: Compose the FastAPI/MCP application and manage its lifecycle,
including startup/shutdown, middleware, and router mounting.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastmcp import FastMCP

from mcp_server_telegram.api_routers import routers as api_routers
from mcp_server_telegram.hybrid_routers import routers as hybrid_routers
from mcp_server_telegram.mcp_routers import routers as mcp_routers
from mcp_server_telegram.middlewares import X402WrapperMiddleware
from mcp_server_telegram.x402_config import get_x402_settings

logger = logging.getLogger(__name__)


# --- Lifespan Management ---
@asynccontextmanager
async def app_lifespan(app: FastAPI):
    """
    Manages the application's resources.

    Note: The Telegram service uses cached instances via lru_cache,
    and the x402 middleware manages its own HTTP client lifecycle using
    context managers, so no external resource management is needed.
    """
    logger.info("Lifespan: Initializing application services...")
    logger.info("Lifespan: Telegram service uses cached instances (no explicit init).")
    logger.info("Lifespan: Services initialized successfully.")
    yield
    logger.info("Lifespan: Shutting down application services...")
    logger.info("Lifespan: Services shut down gracefully.")


# --- Application Factory ---
def create_app() -> FastAPI:
    """
    Create and configure the main FastAPI application.

    This factory function:
    1. Creates an MCP server from hybrid and MCP-only routers
    2. Combines lifespans for proper resource management
    3. Configures API routes with appropriate prefixes
    4. Sets up x402 payment middleware
    5. Validates pricing configuration against available routes

    Returns:
        Configured FastAPI application ready to serve requests
    """
    # --- MCP Server Generation ---
    # Create a FastAPI app containing only MCP-exposed endpoints
    mcp_source_app = FastAPI(title="MCP Source")
    for router in hybrid_routers:
        mcp_source_app.include_router(router)
    for router in mcp_routers:
        mcp_source_app.include_router(router)

    # Convert to MCP server
    mcp_server = FastMCP.from_fastapi(app=mcp_source_app, name="telegram")
    mcp_app = mcp_server.http_app(path="/")

    # --- Combined Lifespan ---
    # This correctly manages both our app's resources and FastMCP's internal state.
    @asynccontextmanager
    async def combined_lifespan(app: FastAPI):
        async with app_lifespan(app):
            async with mcp_app.lifespan(app):
                yield

    # --- Main Application ---
    app = FastAPI(
        title="Telegram MCP Server",
        description="MCP server for sending messages to Telegram channels",
        version="1.0.0",
        lifespan=combined_lifespan,
    )

    # --- Router Configuration ---
    # API-only routes: accessible via /api/* (REST only)
    for router in api_routers:
        app.include_router(router, prefix="/api")

    # Hybrid routes: accessible via /hybrid/* (REST) and /mcp (MCP)
    for router in hybrid_routers:
        app.include_router(router, prefix="/hybrid")

    # MCP-only routes: NOT mounted as REST endpoints
    # They're only accessible through the /mcp endpoint below

    # Mount the MCP server at /mcp
    app.mount("/mcp", mcp_app)

    # --- Pricing Configuration Validation ---
    # First, validate that pricing_mode is consistent with pricing config
    # This will fail fast if pricing_mode='on' but no config exists
    x402_settings = get_x402_settings()
    x402_settings.validate_pricing_mode()

    # Note: validate_against_routes is only available when pricing is configured
    # Since pricing_mode defaults to 'off' for this server, skip route validation

    # --- Middleware Configuration ---
    if x402_settings.pricing_mode == "on":
        app.add_middleware(X402WrapperMiddleware, tool_pricing=x402_settings.pricing)
        logger.info("x402 payment middleware enabled.")
    else:
        logger.info("x402 payment middleware disabled (pricing_mode='off').")

    logger.info("Application setup complete.")
    return app
