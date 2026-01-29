#!/bin/bash
# Start Lurky MCP Server

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if PostgreSQL container is running
if ! docker ps | grep -q lurky-cache-postgres; then
    echo "PostgreSQL container is not running. Starting it..."
    "$SCRIPT_DIR/start_db.sh"
    echo ""
fi

echo "Starting Lurky MCP Server..."
echo "Server will be available at: http://localhost:8000"
echo "API docs: http://localhost:8000/docs"
echo "MCP endpoint: http://localhost:8000/mcp/"
echo ""

# Start the server (using Python 3.12 to avoid compatibility issues with 3.14)
uv run --python 3.12 python -m mcp_server_lurky
