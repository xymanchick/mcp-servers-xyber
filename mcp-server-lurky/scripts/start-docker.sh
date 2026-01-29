#!/bin/bash
# Start Lurky MCP Server in Docker

set -e  # Exit on error

# Default values
RESTART=false
REBUILD=false
PORT=8000
CONTAINER_NAME="mcp-server-lurky"
IMAGE_NAME="mcp-server-lurky"
NETWORK_NAME="mcp-servers-network"

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --restart)
            RESTART=true
            shift
            ;;
        --rebuild)
            REBUILD=true
            RESTART=true  # Rebuild implies restart
            shift
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        --container-name)
            CONTAINER_NAME="$2"
            shift 2
            ;;
        --image-name)
            IMAGE_NAME="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --restart              Stop the container if running and restart it"
            echo "  --rebuild              Rebuild Docker image and restart"
            echo "  --port PORT            Specify port (default: 8000)"
            echo "  --container-name NAME  Specify container name (default: mcp-server-lurky)"
            echo "  --image-name NAME      Specify image name (default: mcp-server-lurky)"
            echo "  --help, -h             Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                     # Start server in Docker"
            echo "  $0 --rebuild           # Rebuild and start"
            echo "  $0 --restart --port 8001  # Restart on different port"
            echo ""
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Change to project root
cd "$PROJECT_ROOT"

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo "Error: Docker is not running. Please start Docker first."
    exit 1
fi

# Function to check if container is running
is_container_running() {
    docker ps --format "{{.Names}}" | grep -q "^${CONTAINER_NAME}$"
}

# Function to stop container
stop_container() {
    if is_container_running; then
        echo "Stopping container ${CONTAINER_NAME}..."
        docker stop "${CONTAINER_NAME}" > /dev/null 2>&1 || true
        echo "Container stopped."
    else
        echo "Container ${CONTAINER_NAME} is not running."
    fi
}

# Function to remove container
remove_container() {
    if docker ps -a --format "{{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
        echo "Removing container ${CONTAINER_NAME}..."
        docker rm "${CONTAINER_NAME}" > /dev/null 2>&1 || true
        echo "Container removed."
    fi
}

# Handle restart
if [ "$RESTART" = true ]; then
    stop_container
    remove_container
    echo "Waiting 2 seconds before restarting..."
    sleep 2
fi

# Handle rebuild
if [ "$REBUILD" = true ]; then
    echo "Rebuilding Docker image ${IMAGE_NAME}..."
    docker build -t "${IMAGE_NAME}" .
    echo "Image rebuilt."
    echo ""
fi

# Check if PostgreSQL container is running
POSTGRES_CONTAINER="lurky-cache-postgres"
POSTGRES_RUNNING=false

if docker ps | grep -q "${POSTGRES_CONTAINER}"; then
    POSTGRES_RUNNING=true
    echo "Found PostgreSQL container: ${POSTGRES_CONTAINER}"
elif docker ps --format "{{.Names}}" --filter "publish=5432" | grep -q .; then
    EXISTING_PG=$(docker ps --format "{{.Names}}" --filter "publish=5432" | head -n1)
    echo "Found existing PostgreSQL container on port 5432: ${EXISTING_PG}"
    POSTGRES_CONTAINER="${EXISTING_PG}"
    POSTGRES_RUNNING=true
else
    echo "PostgreSQL container is not running. Starting it..."
    "$SCRIPT_DIR/start_db.sh"
    echo ""
    POSTGRES_RUNNING=true
fi

# Check if .env file exists
ENV_FILE="${PROJECT_ROOT}/.env"
if [ ! -f "$ENV_FILE" ]; then
    echo "Warning: .env file not found at ${ENV_FILE}"
    echo "Creating a basic .env file with defaults..."
    cat > "$ENV_FILE" << EOF
# Lurky API Settings
LURKY_API_KEY=your_lurky_api_key_here
LURKY_BASE_URL=https://api.lurky.app

# Database Settings
DB_NAME=lurky_db
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=${POSTGRES_CONTAINER}
DB_PORT=5432

# Server Settings
HOST=0.0.0.0
PORT=8000
HOT_RELOAD=false

# x402 Payment Settings (optional)
MCP_LURKY_X402_PRICING_MODE=off
EOF
    echo "Created .env file. Please update it with your actual values."
    echo ""
fi

# Create Docker network if it doesn't exist (for container communication)
if ! docker network ls | grep -q "${NETWORK_NAME}"; then
    echo "Creating Docker network ${NETWORK_NAME}..."
    docker network create "${NETWORK_NAME}" > /dev/null 2>&1 || true
fi

# Check if image exists
if ! docker images --format "{{.Repository}}" | grep -q "^${IMAGE_NAME}$"; then
    echo "Docker image ${IMAGE_NAME} not found. Building it..."
    docker build -t "${IMAGE_NAME}" .
    echo ""
fi

echo "Starting Lurky MCP Server in Docker..."
echo "Container: ${CONTAINER_NAME}"
echo "Image: ${IMAGE_NAME}"
echo "Port: ${PORT}"
echo "Server will be available at: http://localhost:${PORT}"
echo "API docs: http://localhost:${PORT}/docs"
echo "MCP endpoint: http://localhost:${PORT}/mcp/"
echo ""

# Build docker run command
DOCKER_RUN_CMD=(
    docker run
    -d
    --name "${CONTAINER_NAME}"
    -p "${PORT}:8000"
    --env-file "${ENV_FILE}"
    --network "${NETWORK_NAME}"
    --restart unless-stopped
)

# Link to PostgreSQL container if it's in the same network
if docker network inspect "${NETWORK_NAME}" --format '{{range .Containers}}{{.Name}} {{end}}' | grep -q "${POSTGRES_CONTAINER}"; then
    echo "PostgreSQL container is in the same network. Using network connection."
elif [ "${POSTGRES_CONTAINER}" = "lurky-cache-postgres" ]; then
    # Connect PostgreSQL to network if it's our container
    if docker ps | grep -q "${POSTGRES_CONTAINER}"; then
        echo "Connecting PostgreSQL container to network..."
        docker network connect "${NETWORK_NAME}" "${POSTGRES_CONTAINER}" 2>/dev/null || true
    fi
fi

# Add the image name
DOCKER_RUN_CMD+=("${IMAGE_NAME}")

# Run the container
echo "Starting container..."
if "${DOCKER_RUN_CMD[@]}"; then
    echo ""
    echo "✓ Container started successfully!"
    echo ""
    echo "Useful commands:"
    echo "  docker logs -f ${CONTAINER_NAME}     # View logs"
    echo "  docker stop ${CONTAINER_NAME}       # Stop container"
    echo "  docker restart ${CONTAINER_NAME}     # Restart container"
    echo "  docker exec -it ${CONTAINER_NAME} bash  # Access container shell"
    echo ""
    echo "Viewing logs (Ctrl+C to exit):"
    echo ""
    sleep 2
    docker logs -f "${CONTAINER_NAME}"
else
    echo ""
    echo "✗ Failed to start container. Check the error above."
    exit 1
fi
