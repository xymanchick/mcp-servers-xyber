#!/bin/bash
# Start ElevenLabs MCP Server

set -e

echo "Starting ElevenLabs MCP Server..."
echo "Server will be available at: http://localhost:8000"
echo "API docs: http://localhost:8000/docs"
echo ""

# Use Python 3.12
uv run --python 3.12 python -m mcp_server_elevenlabs
