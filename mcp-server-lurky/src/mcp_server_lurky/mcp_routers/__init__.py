"""
Main responsibility: Collect MCP-only FastAPI routers into a single list for inclusion in the MCP source application.
"""

from fastapi import APIRouter

from .spaces import router as spaces_router

routers: list[APIRouter] = [
    spaces_router,
]
