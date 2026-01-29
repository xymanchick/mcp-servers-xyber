# Lurky MCP Server

An MCP (Model Context Protocol) server for searching and parsing Twitter Spaces summaries using the Lurky API. This server provides both an MCP interface for AI agents and a standard REST API, with integrated x402 payment support.

## Features

-   **Twitter Spaces Search**: Find discussions and summaries by keyword.
-   **Space Details & Summaries**: Get deep-dive summaries, TL;DRs, and sentiment analysis for specific Twitter Spaces.
-   **Latest Summaries**: Quickly fetch the most recent summaries for any topic.
-   **Smart Caching**: Local PostgreSQL cache to minimize API calls and reduce costs.
-   **Hybrid Interface**: Support for both MCP tools and standard REST endpoints.
-   **Monetization**: Built-in x402 payment protocol support for monetizing tools and endpoints.

## Prerequisites

-   Python 3.12 or higher
-   [uv](https://github.com/astral-sh/uv) (recommended)
-   PostgreSQL database
-   Lurky API Key (get one at [lurky.app](https://lurky.app))

## Installation

1.  Clone the repository:
    ```bash
    git clone <repository-url>
    cd mcp-server-lurky
    ```

2.  Create a `.env` file from the example:
    ```bash
    LURKY_API_KEY=your_lurky_api_key_here
    LURKY_BASE_URL=https://api.lurky.app
    DB_NAME=lurky_db
    DB_USER=postgres
    DB_PASSWORD=postgres
    DB_HOST=localhost
    DB_PORT=5432
    ```

3.  Install dependencies:
    ```bash
    uv sync
    ```

## Usage

### Running the Server

Start the FastAPI/MCP server:

```bash
uv run python -m mcp_server_lurky
```

The server will be available at `http://0.0.0.0:8000`.

### MCP Integration

The MCP server is mounted at `http://0.0.0.0:8000/mcp`. You can use it with any MCP-compatible client.

**Available MCP Tools:**

-   `lurky_search_spaces`: Search for Twitter Spaces discussions based on a keyword.
-   `lurky_get_space_details`: Get full details, summary, and segmented discussions for a specific Space ID.
-   `lurky_get_latest_summaries`: Fetch the latest N unique Twitter Space summaries for a given topic.

### REST API

-   `GET /api/health`: Health check.
-   `GET /hybrid/search?q=keyword`: Search for spaces.
-   `GET /hybrid/spaces/{space_id}`: Get space details.
-   `GET /hybrid/latest-summaries?topic=topic`: Get latest summaries.

## x402 Payment Integration

This server uses the x402 protocol for monetization. Pricing for each tool and endpoint is defined in `tool_pricing.yaml`.

To enable payments, configure the following in your `.env`:
```bash
MCP_LURKY_X402_PRICING_MODE=on
MCP_LURKY_X402_PAYEE_WALLET_ADDRESS=your_wallet_address
MCP_LURKY_X402_CDP_API_KEY_ID=your_cdp_id
MCP_LURKY_X402_CDP_API_KEY_SECRET=your_cdp_secret
```

## Running the Server

You can run the server in two ways:

### Option 1: Docker (Recommended for Production)

See the [Docker](#docker) section below for instructions on running in Docker.

### Option 2: Local Development

### Using the Start Script (Recommended for Local)

The easiest way to start the server locally is using the provided script:

```bash
# Make sure scripts are executable
chmod +x scripts/*.sh

# Start the server (will automatically start PostgreSQL if needed)
./scripts/start-server.sh
```

The script will:
- Check if PostgreSQL is running and start it if needed
- Start the server on `http://localhost:8000`
- Display API docs and MCP endpoint URLs

### Manual Start

Start PostgreSQL first (if not already running):

```bash
./scripts/start_db.sh
```

Then start the server:

```bash
uv run --python 3.12 python -m mcp_server_lurky
```

The server will be available at:
- **API**: `http://localhost:8000`
- **API Docs**: `http://localhost:8000/docs`
- **MCP Endpoint**: `http://localhost:8000/mcp/`

## Docker

### Using the Docker Start Script (Recommended)

The easiest way to run the server in Docker:

```bash
# Make sure scripts are executable
chmod +x scripts/*.sh

# Start the server in Docker (will build image if needed)
./scripts/start-docker.sh

# Rebuild and restart
./scripts/start-docker.sh --rebuild

# Restart on a different port
./scripts/start-docker.sh --restart --port 8001
```

The script will:
- Check if Docker is running
- Build the Docker image if it doesn't exist
- Start PostgreSQL container if needed
- Create a Docker network for container communication
- Start the server container with proper configuration
- Show logs automatically

**Available options:**
- `--restart` - Stop and restart the container
- `--rebuild` - Rebuild the Docker image and restart
- `--port PORT` - Specify a custom port (default: 8000)
- `--container-name NAME` - Custom container name
- `--image-name NAME` - Custom image name
- `--help` - Show help message

### Manual Docker Commands

You can also run Docker commands manually:

```bash
# Build the image
docker build -t mcp-server-lurky .

# Run the container
docker run -d \
  --name mcp-server-lurky \
  -p 8000:8000 \
  --env-file .env \
  --restart unless-stopped \
  mcp-server-lurky

# View logs
docker logs -f mcp-server-lurky

# Stop the container
docker stop mcp-server-lurky

# Remove the container
docker rm mcp-server-lurky
```

### Docker Compose

If you have Docker Compose available in the parent directory:

```bash
docker-compose up mcp-server-lurky
```

## Testing

Run tests using pytest:

```bash
# Install test dependencies
uv sync --group dev

# Run all tests
uv run pytest

# Run specific test files
uv run pytest tests/test_api_routers.py
uv run pytest tests/test_mcp_tools.py

# Run with coverage
uv run pytest --cov=mcp_server_lurky --cov-report=html
```

**Note**: MCP integration tests (`test_mcp_tools.py`) require a running server. Start the server first, then run:

```bash
uv run pytest tests/test_mcp_tools.py -m integration
```

## License

MIT
