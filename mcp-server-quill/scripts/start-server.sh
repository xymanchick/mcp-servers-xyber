#!/bin/bash
# Start Quill MCP Server

# --- Configuration ---
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# --- Helper Functions ---
print_success() { echo -e "${GREEN}$1${NC}"; }
print_error() { echo -e "${RED}$1${NC}"; }

check_requirements() {
    if ! command -v uv &> /dev/null; then
        print_error "Error: 'uv' is not installed. Please install it first."
        exit 1
    fi
}

setup_env() {
    if [ ! -f "$PROJECT_ROOT/.env" ]; then
        if [ -f "$PROJECT_ROOT/.example.env" ]; then
            echo "Creating .env from .example.env..."
            cp "$PROJECT_ROOT/.example.env" "$PROJECT_ROOT/.env"
            print_success "Created .env file. Please edit it with your API keys!"
        else
            print_error "Error: .example.env not found."
            exit 1
        fi
    fi
}

# --- Main Script ---
check_requirements
setup_env

echo "Starting Quill MCP Server..."
echo "Server will be available at: http://localhost:8001"
echo "API docs: http://localhost:8001/docs"
echo "MCP endpoint: http://localhost:8001/mcp/"
echo ""

# Start the server using uv
cd "$PROJECT_ROOT"
uv run --python 3.12 python -m mcp_server_quill
