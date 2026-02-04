"""
Collect API-only FastAPI routers into a single list.

Main responsibility: Aggregate all API-only routers for REST-only access.
"""

from fastapi import APIRouter

from .health import router as health_router

routers: list[APIRouter] = [
    health_router,
]
