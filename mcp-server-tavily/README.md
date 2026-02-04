# MCP Server - Tavily Web Search

> **General:** This repository provides an MCP (Model Context Protocol) server implementation for interacting with the Tavily AI web search API.
> It demonstrates a **hybrid architecture** that exposes functionality through REST APIs, MCP, or both simultaneously.

## Capabilities

### 1. **API-Only Endpoints** (`/api`)

Standard REST endpoints for traditional clients (e.g., web apps, dashboards).

| Method | Endpoint              | Price      | Description                            |
| :----- | :-------------------- | :--------- | :------------------------------------- |
| `GET`  | `/api/health`         | **Free**   | Checks the server's operational status |

### 2. **Hybrid Endpoints** (`/hybrid`)

Accessible via both REST and as MCP tools. Ideal for functionality shared between humans and AI.

| Method/Tool                 | Price      | Description                                                  |
| :-------------------------- | :--------- | :----------------------------------------------------------- |
| `GET /hybrid/pricing`       | **Free**   | Returns tool pricing configuration                           |
| `tavily_web_search`         | **Paid**   | Performs a web search using Tavily API (query, max_results)  |

*Note: Paid endpoints require x402 payment protocol configuration. See `env.example` for details.*

## API Documentation

This server automatically generates OpenAPI documentation. Once the server is running, you can access the interactive API docs at:

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs) (for REST endpoints)
- **MCP Inspector**: Use an MCP-compatible client to view available agent tools [http://localhost:8000/mcp](http://localhost:8000/mcp)

These interfaces allow you to explore all REST-accessible endpoints, view their schemas, and test them directly from your browser.

## Requirements

- **Python 3.12+**
- **UV** (for dependency management)
- **Tavily AI API Key**
- **Docker** (optional, for containerization)

## Setup

1.  **Clone & Configure**
    ```bash
    git clone <repository-url>
    cd mcp-server-tavily
    cp env.example .env
    # Configure environment for Tavily API key, x402, logging, etc. (see env.example).
    ```

2.  **Virtual Environment**
    ```bash
    # working directory: ./mcp-servers/mcp-server-tavily/
    uv sync
    ```

## Running the Server

### Using Docker Compose (Recommended)

From the root `mcp-servers` directory, you can run the service for production or development.

```bash
# path: ./mcp-servers
# Run the production container
docker compose up mcp_server_tavily

# Run the development container with hot-reloading
docker compose -f docker-compose.debug.yml up mcp_server_tavily
```

### Locally

```bash
# path: ./mcp-servers/mcp-server-tavily/
# Basic run
uv run python -m mcp_server_tavily

# Or with custom port and host
uv run python -m mcp_server_tavily --port 8000 --reload
```

### Using Docker (Standalone)

```bash
# path: ./mcp-servers/mcp-server-tavily/
# Build the image
docker build -t mcp-server-tavily .

# Run the container
docker run --rm -it -p 8000:8000 --env-file .env mcp-server-tavily
```

## Testing

```bash
# path: ./mcp-servers/mcp-server-tavily/
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v
```

## Project Structure

```
mcp-server-tavily/
├── src/
│   └── mcp_server_tavily/
│       ├── __init__.py
│       ├── __main__.py              # Entry point (CLI + uvicorn)
│       ├── app.py                   # Application factory & lifespan
│       ├── config.py                # Settings with lru_cache factories
│       ├── logging_config.py        # Logging configuration
│       ├── dependencies.py          # FastAPI dependency injection
│       ├── schemas.py               # Pydantic request/response models
│       ├── x402_config.py           # x402 payment configuration
│       │
│       ├── api_routers/             # API-Only endpoints (REST)
│       │   ├── __init__.py
│       │   └── health.py            # Health check endpoint
│       ├── hybrid_routers/          # Hybrid endpoints (REST + MCP)
│       │   ├── __init__.py
│       │   ├── pricing.py           # Pricing information endpoint
│       │   └── search.py            # Tavily web search endpoint
│       ├── middlewares/
│       │   ├── __init__.py
│       │   └── x402_wrapper.py      # x402 payment middleware
│       │
│       └── tavily/                  # Business logic layer
│           ├── __init__.py
│           ├── config.py
│           ├── models.py
│           ├── module.py
│           └── errors.py
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
