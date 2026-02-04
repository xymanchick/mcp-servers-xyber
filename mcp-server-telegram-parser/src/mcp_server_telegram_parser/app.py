import logging

from fastapi import FastAPI
from fastmcp import FastMCP

from mcp_server_telegram_parser.api_routers import routers as api_routers
from mcp_server_telegram_parser.hybrid_routers import routers as hybrid_routers
from mcp_server_telegram_parser.mcp_routers import routers as mcp_routers
from mcp_server_telegram_parser.x402_config import get_x402_settings

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    # --- MCP Server Generation ---
    mcp_source_app = FastAPI(title="MCP Source")
    # Include hybrid routers in MCP source
    for router in hybrid_routers:
        mcp_source_app.include_router(router)
    # Include MCP-only routers in MCP source
    for router in mcp_routers:
        mcp_source_app.include_router(router)

    # Convert to MCP server
    mcp_server = FastMCP.from_fastapi(app=mcp_source_app, name="telegram-parser")
    mcp_app = mcp_server.http_app(path="/")

    # --- Main Application ---
    app = FastAPI(
        title="Telegram Parser MCP Server",
        description="Parses public Telegram channels via Telethon",
        version="1.0.0",
        lifespan=mcp_app.lifespan,
    )

    # --- Router Configuration ---
    # API-only routes
    for router in api_routers:
        app.include_router(router, prefix="/api")

    # Hybrid routes
    for router in hybrid_routers:
        app.include_router(router, prefix="/hybrid")

    # Mount the MCP server at /mcp
    app.mount("/mcp", mcp_app)

    # --- Pricing Configuration Validation ---
    x402_settings = get_x402_settings()
    x402_settings.validate_pricing_mode()

    # Validate that all priced endpoints actually exist
    all_routes = app.routes + mcp_source_app.routes
    x402_settings.validate_against_routes(all_routes)

    # --- Middleware Configuration ---
    if x402_settings.pricing_mode == "on":
        from mcp_server_telegram_parser.middlewares import X402WrapperMiddleware
        app.add_middleware(X402WrapperMiddleware, tool_pricing=x402_settings.pricing)
        logger.info("x402 payment middleware enabled.")
    else:
        logger.info("x402 payment middleware disabled (pricing_mode='off').")

    logger.info("Application setup complete.")
    return app
