import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastmcp import FastMCP
from mcp_server_twitter.api_routers import routers as api_routers
from mcp_server_twitter.dependencies import DependencyContainer
from mcp_server_twitter.hybrid_routers import routers as hybrid_routers
from mcp_server_twitter.logging_config import get_logger
from mcp_server_twitter.mcp_routers import routers as mcp_routers
from mcp_server_twitter.metrics import (get_health_checker,
                                        get_metrics_collector)
from mcp_server_twitter.x402_config import get_x402_settings

logger = get_logger(__name__)


async def periodic_metrics_logging(interval_seconds: int):
    """Periodically log metrics summary."""
    while True:
        try:
            await asyncio.sleep(interval_seconds)

            metrics_collector = get_metrics_collector()
            health_checker = get_health_checker()

            # Log metrics summary
            metrics_collector.log_summary()

            # Log health status
            health_status = health_checker.get_health_status()
            logger.info(
                f"Health check: {health_status['status']}",
                extra={"health_status": health_status},
            )

        except asyncio.CancelledError:
            logger.info("Metrics logging task cancelled")
            break
        except Exception as e:
            logger.error(
                "Error in periodic metrics logging",
                extra={"error_type": type(e).__name__},
                exc_info=True,
            )


# --- Lifespan Management ---
@asynccontextmanager
async def app_lifespan(app: FastAPI):
    """
    Manages the application's resources.

    Currently manages:
    - AsyncTwitterClient for Twitter API calls
    - Periodic metrics logging task
    """
    logger.info("Lifespan: Initializing application services...")

    # Start metrics logging task if enabled
    metrics_task = None
    if os.getenv("ENABLE_METRICS", "true").lower() in ("true", "1", "yes"):
        metrics_interval = int(
            os.getenv("METRICS_LOG_INTERVAL", "300")
        )  # 5 minutes default
        metrics_task = asyncio.create_task(periodic_metrics_logging(metrics_interval))
        logger.info(f"Metrics logging enabled with {metrics_interval}s interval")

    try:
        # Initialize Twitter client
        logger.info("Lifespan: Initializing Twitter client...")
        await DependencyContainer.initialize()

        # Log initial health status
        health_checker = get_health_checker()
        health_status = health_checker.get_health_status()
        logger.info(
            "Server startup completed",
            extra={
                "startup_health": health_status,
                "client_type": type(DependencyContainer.get_twitter_client()).__name__,
            },
        )

        logger.info("Lifespan: Services initialized successfully.")
        yield

    except Exception as init_err:
        logger.error(
            "FATAL: Server startup failed",
            extra={
                "error_type": type(init_err).__name__,
                "error_message": str(init_err),
            },
            exc_info=True,
        )
        raise init_err

    finally:
        logger.info("Lifespan: Shutting down application services...")

        # Cancel metrics task
        if metrics_task:
            metrics_task.cancel()
            try:
                await metrics_task
            except asyncio.CancelledError:
                pass

        # Log final metrics summary
        metrics_collector = get_metrics_collector()
        metrics_collector.log_summary()

        await DependencyContainer.shutdown()

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
    mcp_server = FastMCP.from_fastapi(app=mcp_source_app, name="Twitter")
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
        title="Twitter MCP Server (Hybrid)",
        description="A server with REST, MCP, and x402 payment capabilities.",
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

    # Then validate that all priced endpoints actually exist
    # and warn about any misconfiguration
    all_routes = app.routes + mcp_source_app.routes
    x402_settings.validate_against_routes(all_routes)

    # --- Middleware Configuration ---
    if x402_settings.pricing_mode == "on":
        from mcp_server_twitter.middlewares import X402WrapperMiddleware

        app.add_middleware(X402WrapperMiddleware, tool_pricing=x402_settings.pricing)
        logger.info("x402 payment middleware enabled.")
    else:
        logger.info("x402 payment middleware disabled (pricing_mode='off').")

    logger.info("Application setup complete.")
    return app
