import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastmcp import FastMCP

from mcp_server_quill.api_routers import routers as api_routers
from mcp_server_quill.hybrid_routers import routers as hybrid_routers
from mcp_server_quill.mcp_routers import routers as mcp_only_routers

logger = logging.getLogger(__name__)


@asynccontextmanager
async def app_lifespan(app: FastAPI):
    """
    Manages the application's resources.
    """
    logger.info("Lifespan: Initializing application services...")
    yield
    logger.info("Lifespan: Shutting down application services...")


def create_app() -> FastAPI:
    """
    Create and configure the main FastAPI application.
    """
    # --- MCP Server Generation ---
    # Create a FastAPI app containing only MCP-exposed endpoints
    mcp_source_app = FastAPI(title="MCP Source")
    
    # Add hybrid routers (REST + MCP)
    for router in hybrid_routers:
        mcp_source_app.include_router(router)
        
    # Add MCP-only routers (MCP only)
    for router in mcp_only_routers:
        mcp_source_app.include_router(router)

    # Convert to MCP server
    mcp_server = FastMCP.from_fastapi(app=mcp_source_app, name="MCP")
    mcp_app = mcp_server.http_app(path="/")

    # --- Combined Lifespan ---
    @asynccontextmanager
    async def combined_lifespan(app: FastAPI):
        async with app_lifespan(app):
            async with mcp_app.lifespan(app):
                yield

    # --- Main Application ---
    app = FastAPI(
        title="Quill MCP Server",
        description="A server with REST and MCP capabilities for Quill Token Security.",
        version="0.2.0",
        lifespan=combined_lifespan,
    )

    # --- Router Configuration ---
    # API-only routes: accessible via /api/* (REST only)
    for router in api_routers:
        app.include_router(router, prefix="/api")

    # Hybrid routes: accessible via /hybrid/* (REST) and /mcp (MCP)
    for router in hybrid_routers:
        app.include_router(router, prefix="/hybrid")

    # Mount the MCP server at /mcp
    app.mount("/mcp", mcp_app)

    logger.info("Application setup complete.")
    return app
