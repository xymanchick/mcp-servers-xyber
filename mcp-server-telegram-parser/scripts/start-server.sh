#!/bin/bash
# Start Telegram Parser MCP Server

set -e

echo "Starting Telegram Parser MCP Server..."
echo "Server will be available at: http://localhost:8012"
echo "API docs: http://localhost:8012/docs"
echo "MCP endpoint: http://localhost:8012/mcp/"
echo ""

# Use Python 3.12 for consistency with other MCP servers
uv run --python 3.12 python -m mcp_server_telegram_parser
