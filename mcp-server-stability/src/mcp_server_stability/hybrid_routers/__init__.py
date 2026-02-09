from mcp_server_stability.hybrid_routers.generate_image import \
    router as generate_image_router
from mcp_server_stability.hybrid_routers.pricing import \
    router as pricing_router

routers = [pricing_router, generate_image_router]
