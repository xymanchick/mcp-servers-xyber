from mcp_server_qdrant.hybrid_routers.pricing import router as pricing_router
from mcp_server_qdrant.hybrid_routers.qdrant_tools import \
    router as qdrant_tools_router

routers = [pricing_router, qdrant_tools_router]
