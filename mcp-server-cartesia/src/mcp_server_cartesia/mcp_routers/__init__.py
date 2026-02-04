"""
Collect MCP-only FastAPI routers into a single list.

Main responsibility: Aggregate all MCP-only routers for inclusion in the MCP source application.
"""

from fastapi import APIRouter

from .tts import router as tts_router

routers: list[APIRouter] = [
    tts_router,
]
