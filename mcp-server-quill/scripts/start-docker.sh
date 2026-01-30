#!/bin/bash
# Start Quill MCP Server in Docker

set -e  # Exit on error

# --- Configuration ---
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
RESTART=false
REBUILD=false
PORT=8001
CONTAINER_NAME="mcp-server-quill"
IMAGE_NAME="mcp-server-quill"

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# --- Helper Functions ---
print_success() { echo -e "${GREEN}$1${NC}"; }
print_error() { echo -e "${RED}$1${NC}"; }
print_warning() { echo -e "${YELLOW}$1${NC}"; }

check_docker() {
    if ! docker info &> /dev/null; then
        print_error "Error: Docker is not running. Please start Docker first."
        exit 1
    fi
}

is_container_running() {
    docker ps --format "{{.Names}}" | grep -q "^${CONTAINER_NAME}$"
}

stop_container() {
    if is_container_running; then
        echo "Stopping container ${CONTAINER_NAME}..."
        docker stop "${CONTAINER_NAME}" > /dev/null 2>&1 || true
        print_success "Container stopped."
    fi
}

remove_container() {
    if docker ps -a --format "{{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
        echo "Removing container ${CONTAINER_NAME}..."
        docker rm -f "${CONTAINER_NAME}" > /dev/null 2>&1 || true
        print_success "Container removed."
    fi
}

setup_env() {
    ENV_FILE="${PROJECT_ROOT}/.env"
    if [ ! -f "$ENV_FILE" ]; then
        if [ -f "${PROJECT_ROOT}/.example.env" ]; then
            print_warning "Warning: .env file not found. Creating from .example.env..."
            cp "${PROJECT_ROOT}/.example.env" "$ENV_FILE"
            print_success "Created .env file. Please update it with your actual values."
        else
            print_error "Error: .env file not found and no .example.env available."
            exit 1
        fi
    fi
}

# --- Argument Parsing ---
while [[ $# -gt 0 ]]; do
    case $1 in
        --restart) RESTART=true; shift ;;
        --rebuild) REBUILD=true; RESTART=true; shift ;;
        --port) PORT="$2"; shift 2 ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --restart    Restart container"
            echo "  --rebuild    Rebuild image and restart"
            echo "  --port PORT  Specify port (default: 8001)"
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# --- Main Script ---
check_docker
cd "$PROJECT_ROOT"
setup_env

# Handle cleanup
if [ "$RESTART" = true ]; then
    stop_container
    remove_container
    sleep 1
else
    # Remove if exists but stopped
    if docker ps -a --format "{{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
        if ! is_container_running; then
            echo "Found stopped container. Removing..."
            remove_container
        fi
    fi
fi

# Build image
if [ "$REBUILD" = true ] || ! docker images --format "{{.Repository}}" | grep -q "^${IMAGE_NAME}$"; then
    echo "Building Docker image ${IMAGE_NAME}..."
    docker build -t "${IMAGE_NAME}" .
    print_success "Image built successfully."
fi

# Run container
echo "Starting Quill MCP Server in Docker..."
echo "Container: ${CONTAINER_NAME}"
echo "Port: ${PORT}"

if docker run -d \
    --name "${CONTAINER_NAME}" \
    -p "${PORT}:8001" \
    --env-file "${PROJECT_ROOT}/.env" \
    --restart unless-stopped \
    "${IMAGE_NAME}"; then
    
    print_success "✓ Container started successfully!"
    echo ""
    echo "Server available at: http://localhost:${PORT}"
    echo ""
    echo "Useful commands:"
    echo "  docker logs -f ${CONTAINER_NAME}"
    echo "  docker stop ${CONTAINER_NAME}"
    echo ""
    echo "Tail logs (Ctrl+C to exit):"
    sleep 2
    docker logs -f "${CONTAINER_NAME}"
else
    print_error "✗ Failed to start container."
    exit 1
fi
