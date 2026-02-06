from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastmcp import FastMCP

from mcp_server_elevenlabs.api_routers import routers as api_routers
from mcp_server_elevenlabs.config import get_app_settings
from mcp_server_elevenlabs.hybrid_routers import routers as hybrid_routers
from mcp_server_elevenlabs.mcp_routers import routers as mcp_routers

logger = logging.getLogger(__name__)


@asynccontextmanager
async def app_lifespan(app: FastAPI):
    settings = get_app_settings()
    # Ensure media directory exists
    settings.media.voice_output_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Lifespan: media directory ready at %s", settings.media.voice_output_dir)
    yield


def create_app() -> FastAPI:
    # --- MCP Server Generation ---
    mcp_source_app = FastAPI(title="MCP Source")
    for router in hybrid_routers:
        mcp_source_app.include_router(router)
    for router in mcp_routers:
        mcp_source_app.include_router(router)

    mcp_server = FastMCP.from_fastapi(app=mcp_source_app, name="ElevenLabs")
    mcp_app = mcp_server.http_app(path="/")

    @asynccontextmanager
    async def combined_lifespan(app: FastAPI):
        async with app_lifespan(app):
            async with mcp_app.lifespan(app):
                yield

    # --- Main Application ---
    app = FastAPI(
        title="ElevenLabs MCP Server (Hybrid)",
        description="""
An MCP (Model Context Protocol) server that provides ElevenLabs Text-to-Speech capabilities.

It exposes the same functionality via:

- **REST (Hybrid)**: `/hybrid/*`
- **MCP tools**: mounted at `/mcp` (generated from the same hybrid routes)

### Endpoints

- **API-only**
  - `GET /api/health` — health check
- **Hybrid (REST + MCP)**
  - `POST /hybrid/generate-voice` — generates an MP3 audio file from text
- **Downloads**
  - `GET /hybrid/audio/{filename}` — download generated audio files
""".strip(),
        version="0.1.0",
        lifespan=combined_lifespan,
    )

    # API-only routes
    for router in api_routers:
        app.include_router(router, prefix="/api")

    # Hybrid routes (REST + MCP)
    for router in hybrid_routers:
        app.include_router(router, prefix="/hybrid")

    # Mount the MCP server at /mcp
    app.mount("/mcp", mcp_app)

    logger.info("Application setup complete.")
    return app
