from mcp_server_elevenlabs.api_routers.health import router as health_router
from mcp_server_elevenlabs.api_routers.tts_file import router as tts_file_router

routers = [health_router, tts_file_router]
