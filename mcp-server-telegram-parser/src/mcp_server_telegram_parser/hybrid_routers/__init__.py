from mcp_server_telegram_parser.hybrid_routers.parse_channels import (
    router as parse_channels_router,
)
from mcp_server_telegram_parser.hybrid_routers.pricing import router as pricing_router

routers = [pricing_router, parse_channels_router]
