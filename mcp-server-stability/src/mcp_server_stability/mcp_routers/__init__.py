from fastapi import APIRouter

from .generate_image import router as generate_image_router

routers: list[APIRouter] = [
    generate_image_router,
]
