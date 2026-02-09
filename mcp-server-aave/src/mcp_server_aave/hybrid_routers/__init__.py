from mcp_server_aave.hybrid_routers.available_networks import \
    router as available_networks_router
from mcp_server_aave.hybrid_routers.comprehensive_data import \
    router as comprehensive_data_router
from mcp_server_aave.hybrid_routers.pricing import router as pricing_router

routers = [
    pricing_router,
    available_networks_router,
    comprehensive_data_router,
]
