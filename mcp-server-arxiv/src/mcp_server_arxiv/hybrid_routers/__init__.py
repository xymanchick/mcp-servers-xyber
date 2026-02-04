from fastapi import APIRouter
from .search import router as search_router
from .pricing import router as pricing_router

routers: list[APIRouter] = [
    search_router,
    pricing_router,
]

