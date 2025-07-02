from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mcp_server_youtube.routes import router

app = FastAPI(title="YouTube MCP Server")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the router at /mcp prefix
app.include_router(router, prefix="/mcp", tags=["mcp"])
