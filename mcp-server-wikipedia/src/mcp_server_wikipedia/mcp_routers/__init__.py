from fastapi import APIRouter

from .article import router as article_router
from .links import router as links_router
from .related import router as related_router
from .search import router as search_router
from .sections import router as sections_router
from .summary import router as summary_router

routers: list[APIRouter] = [
    search_router,
    article_router,
    summary_router,
    sections_router,
    links_router,
    related_router,
]
