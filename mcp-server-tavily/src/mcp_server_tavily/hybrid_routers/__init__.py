from .pricing import router as pricing_router
from .search import router as search_router

routers = [
    search_router,
    pricing_router,
]
