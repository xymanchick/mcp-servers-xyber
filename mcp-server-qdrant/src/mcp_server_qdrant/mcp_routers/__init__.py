from fastapi import APIRouter

from .qdrant_tools import router as qdrant_tools_router

routers: list[APIRouter] = [
    qdrant_tools_router,
]
