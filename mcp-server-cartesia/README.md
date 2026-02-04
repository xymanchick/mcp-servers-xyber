# MCP Cartesia Server

> **General:** This repository provides an MCP (Model Context Protocol) server for text-to-speech (TTS) synthesis using the Cartesia API.
> It demonstrates a **hybrid architecture** that exposes functionality through REST APIs, MCP, or both simultaneously.

## Capabilities

### 1. **API-Only Endpoints** (`/api`)

Standard REST endpoints for traditional clients (e.g., web apps, dashboards).

| Method | Endpoint              | Price      | Description                            |
| :----- | :-------------------- | :--------- | :------------------------------------- |
| `GET`  | `/api/health`         | **Free**   | Checks the server's operational status |

### 2. **Hybrid Endpoints** (`/hybrid`)

Accessible via both REST and as MCP tools. Ideal for functionality shared between humans and AI.

| Method/Tool                 | Price      | Description                         |
| :-------------------------- | :--------- | :---------------------------------- |
| `GET /hybrid/pricing`       | **Free**   | Returns tool pricing configuration  |
| `cartesia_get_pricing`      | **Free**   | Returns tool pricing configuration  |

### 3. **MCP-Only Endpoints**

Tools exposed exclusively to AI agents. Not available as REST endpoints.

| Tool                        | Price      | Description                                          |
| :-------------------------- | :--------- | :--------------------------------------------------- |
| `generate_cartesia_tts`     | **Free**   | Synthesizes speech from text and saves as WAV file   |

*Note: Paid endpoints require x402 payment protocol configuration. See `.env.example` for details.*

## API Documentation

This server automatically generates OpenAPI documentation. Once the server is running, you can access the interactive API docs at:

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs) (for REST endpoints)
- **MCP Inspector**: Use an MCP-compatible client to view available agent tools [http://localhost:8000/mcp](http://localhost:8000/mcp)

These interfaces allow you to explore all REST-accessible endpoints, view their schemas, and test them directly from your browser.

## Requirements

- **Python 3.12+**
- **UV** (for dependency management)
- **Cartesia API Key** (required for TTS generation)
- **Docker** (optional, for containerization)

## Setup

1.  **Clone & Configure**
    ```bash
    git clone <repository-url>
    cd mcp-server-cartesia
    cp .env.example .env
    # Configure environment for Cartesia API key, x402, logging, etc. (see .env.example).
    ```

2.  **Virtual Environment**
    ```bash
    # working directory: ./mcp-servers/mcp-server-cartesia/
    uv sync
    ```

## Running the Server

### Using Docker Compose (Recommended)

From the root `mcp-servers` directory, you can run the service for production or development.

```bash
# path: ./mcp-servers
# Run the production container
docker compose up mcp_server_cartesia

# Run the development container with hot-reloading
docker compose -f docker-compose.debug.yml up mcp_server_cartesia
```

### Locally

```bash
# path: ./mcp-servers/mcp-server-cartesia/
# Basic run
uv run python -m mcp_server_cartesia

# Or with custom port and host
uv run python -m mcp_server_cartesia --port 8000 --reload
```

### Using Docker (Standalone)

```bash
# path: ./mcp-servers/mcp-server-cartesia/
# Build the image
docker build -t mcp-server-cartesia .

# Run the container
docker run --rm -it -p 8000:8000 --env-file .env mcp-server-cartesia
```

## Testing

```bash
# path: ./mcp-servers/mcp-server-cartesia/
# Run all tests
uv run pytest
```

## Project Structure

```
mcp-server-cartesia/
├── src/
│   └── mcp_server_cartesia/
│       ├── __init__.py
│       ├── __main__.py              # Entry point (CLI + uvicorn)
│       ├── app.py                   # Application factory & lifespan
│       ├── config.py                # Settings with lru_cache factories
│       ├── logging_config.py        # Logging configuration
│       ├── dependencies.py          # FastAPI dependency injection
│       ├── schemas.py               # Pydantic request/response models
│       ├── client.py                # Cartesia client wrapper
│       │
│       ├── api_routers/             # API-Only endpoints (REST)
│       │   └── health.py            # Health check endpoint
│       ├── hybrid_routers/          # Hybrid endpoints (REST + MCP)
│       │   └── pricing.py           # Pricing configuration
│       ├── mcp_routers/             # MCP-Only endpoints
│       │   └── tts.py               # Text-to-speech generation
│       ├── middlewares/
│       │   └── x402_wrapper.py      # x402 payment middleware
│       ├── x402_config.py           # x402 payment configuration
│       │
│       └── cartesia_client/         # Business logic layer
│           ├── __init__.py
│           ├── config.py
│           └── client.py
│
├── tests/
├── .env.example
├── Dockerfile
├── pyproject.toml
└── README.md
```

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT
