"""
Hybrid routers - available via both REST and MCP.
"""

from fastapi import APIRouter

from .pricing import router as pricing_router
from .search import router as search_router
from .search_videos import router as search_videos_router
from .transcripts import router as transcripts_router

routers: list[APIRouter] = [
    search_router,
    pricing_router,
    search_videos_router,
    transcripts_router,
]
