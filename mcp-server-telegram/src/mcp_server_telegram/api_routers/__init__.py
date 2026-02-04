"""
This module collects REST-only FastAPI routers into a single list for inclusion in the main application.

Main responsibility: Aggregate all API routers for the Telegram server.
"""

from fastapi import APIRouter

from .health import router as health_router

routers: list[APIRouter] = [
    health_router,
]
