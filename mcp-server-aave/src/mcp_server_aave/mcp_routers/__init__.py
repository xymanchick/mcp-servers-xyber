from fastapi import APIRouter

from .available_networks import router as available_networks_router
from .comprehensive_data import router as comprehensive_data_router

routers: list[APIRouter] = [
    available_networks_router,
    comprehensive_data_router,
]
