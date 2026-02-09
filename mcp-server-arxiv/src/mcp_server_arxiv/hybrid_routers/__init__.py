from fastapi import APIRouter

from .pricing import router as pricing_router
from .search import router as search_router

routers: list[APIRouter] = [
    search_router,
    pricing_router,
]
