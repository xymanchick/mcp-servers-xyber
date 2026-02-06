#!/bin/bash
# Start ElevenLabs MCP Server in Docker (standalone)

set -e  # Exit on error

# Default values
RESTART=false
REBUILD=false
PORT=8000
CONTAINER_NAME="mcp-server-elevenlabs"
IMAGE_NAME="mcp-server-elevenlabs"

# Validate flags that require arguments.
require_arg() {
    local flag="$1"
    local value="${2-}"
    if [ -z "$value" ] || [[ "$value" == --* ]]; then
        echo "Error: ${flag} requires a value"
        echo "Use --help for usage information"
        exit 1
    fi
}

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --restart)
            RESTART=true
            shift
            ;;
        --rebuild)
            REBUILD=true
            RESTART=true
            shift
            ;;
        --port)
            require_arg "--port" "${2-}"
            PORT="$2"
            shift 2
            ;;
        --container-name)
            require_arg "--container-name" "${2-}"
            CONTAINER_NAME="$2"
            shift 2
            ;;
        --image-name)
            require_arg "--image-name" "${2-}"
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
            echo "  --container-name NAME  Specify container name (default: mcp-server-elevenlabs)"
            echo "  --image-name NAME      Specify image name (default: mcp-server-elevenlabs)"
            echo "  --help, -h             Show this help message"
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

cd "$PROJECT_ROOT"

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo "Error: Docker is not running. Please start Docker first."
    exit 1
fi

is_container_running() {
    docker ps --format "{{.Names}}" | grep -q "^${CONTAINER_NAME}$"
}

remove_container() {
    if docker ps -a --format "{{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
        echo "Removing container ${CONTAINER_NAME}..."
        docker rm -f "${CONTAINER_NAME}" > /dev/null 2>&1 || true
        echo "Container removed."
    fi
}

if [ "$RESTART" = true ]; then
    if is_container_running; then
        echo "Stopping container ${CONTAINER_NAME}..."
        docker stop "${CONTAINER_NAME}" > /dev/null 2>&1 || true
    fi
    remove_container
    echo "Waiting 2 seconds before restarting..."
    sleep 2
else
    # Remove stopped container with same name
    if docker ps -a --format "{{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
        if ! is_container_running; then
            echo "Found stopped container ${CONTAINER_NAME}. Removing it..."
            remove_container
        fi
    fi
fi

if [ "$REBUILD" = true ]; then
    echo "Rebuilding Docker image ${IMAGE_NAME}..."
    docker build -t "${IMAGE_NAME}" .
    echo "Image rebuilt."
    echo ""
fi

if ! docker images --format "{{.Repository}}" | grep -q "^${IMAGE_NAME}$"; then
    echo "Docker image ${IMAGE_NAME} not found. Building it..."
    docker build -t "${IMAGE_NAME}" .
    echo ""
fi

# Ensure a local voice dir exists if you want persistence on the host.
mkdir -p voice

# Load env for ElevenLabs credentials (recommended: .env file).
# We intentionally do NOT bake secrets into the Docker image.
ENV_FILE_ARGS=()
if [ -f ".env" ]; then
  ENV_FILE_ARGS+=(--env-file ".env")
else
  # Fall back to forwarding env vars from the current shell, if present.
  # (This keeps behavior similar to local runs.)
  if [ -n "${ELEVENLABS_API_KEY-}" ]; then
    ENV_FILE_ARGS+=(-e "ELEVENLABS_API_KEY=${ELEVENLABS_API_KEY}")
  fi
  if [ -n "${ELEVENLABS_VOICE_ID-}" ]; then
    ENV_FILE_ARGS+=(-e "ELEVENLABS_VOICE_ID=${ELEVENLABS_VOICE_ID}")
  fi
  if [ -n "${ELEVENLABS_MODEL_ID-}" ]; then
    ENV_FILE_ARGS+=(-e "ELEVENLABS_MODEL_ID=${ELEVENLABS_MODEL_ID}")
  fi
fi

if [ -z "${ELEVENLABS_API_KEY-}" ] && [ ! -f ".env" ]; then
  echo "Warning: ELEVENLABS_API_KEY is not set and .env was not found."
  echo "         The TTS endpoint/tool will return 400 until you provide it."
  echo "         Fix: create .env (recommended) or export ELEVENLABS_API_KEY before running."
  echo ""
fi

echo "Starting ElevenLabs MCP Server in Docker..."
echo "Container: ${CONTAINER_NAME}"
echo "Image: ${IMAGE_NAME}"
echo "Network: host (sharing host network stack)"
echo "Server will be available at: http://localhost:${PORT}"
echo "API docs: http://localhost:${PORT}/docs"
echo "MCP endpoint: http://localhost:${PORT}/mcp/"
echo ""

docker run -d \
  --name "${CONTAINER_NAME}" \
  --network host \
  "${ENV_FILE_ARGS[@]}" \
  -e "HOST=0.0.0.0" \
  -e "PORT=${PORT}" \
  -v "$(pwd)/voice:/app/media/voice" \
  --restart unless-stopped \
  "${IMAGE_NAME}"

echo ""
echo "✓ Container started successfully!"
echo ""
echo "Useful commands:"
echo "  docker logs -f ${CONTAINER_NAME}     # View logs"
echo "  docker stop ${CONTAINER_NAME}       # Stop container"
echo "  docker restart ${CONTAINER_NAME}     # Restart container"
echo "  docker exec -it ${CONTAINER_NAME} bash  # Access container shell"
