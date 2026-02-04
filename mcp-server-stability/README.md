# MCP Stability Server

> **General:** This repository provides an MCP (Model Context Protocol) server for Stability AI image generation.
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

### 3. **MCP-Only Endpoints**

Tools exposed exclusively to AI agents. Not available as REST endpoints.

| Tool                    | Price      | Description                               |
| :---------------------- | :--------- | :---------------------------------------- |
| `generate_image`        | **Paid**   | Generates an image from a text prompt using Stability AI |

#### `generate_image` Tool Details:
- **Input:**
    - `prompt` (required): A text description of the image to generate.
    - `negative_prompt` (optional): A text description of what to avoid in the image.
    - `aspect_ratio` (optional): The aspect ratio of the generated image (e.g., "16:9", "1:1").
    - `seed` (optional): A seed for reproducible generation.
    - `style_preset` (optional): A preset style to guide the generation (e.g., "photographic", "anime").
- **Output:** The generated image as PNG bytes.

*Note: Paid endpoints require x402 payment protocol configuration. See `.env.example` for details.*

## API Documentation

This server automatically generates OpenAPI documentation. Once the server is running, you can access the interactive API docs at:

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs) (for REST endpoints)
- **MCP Inspector**: Use an MCP-compatible client to view available agent tools [http://localhost:8000/mcp](http://localhost:8000/mcp)

These interfaces allow you to explore all REST-accessible endpoints, view their schemas, and test them directly from your browser.

## Requirements

- **Python 3.12+**
- **UV** (for dependency management)
- **Stability AI API Key** (required for image generation)
- **Docker** (optional, for containerization)

## Setup

1.  **Clone & Configure**
    ```bash
    git clone <repository-url>
    cd mcp-server-stability
    cp .env.example .env
    # Configure environment with your Stability AI API key and x402 settings (see .env.example).
    ```

2.  **Virtual Environment**
    ```bash
    # working directory: ./mcp-servers/mcp-server-stability/
    uv sync
    ```

## Running the Server

### Using Docker Compose (Recommended)

From the root `mcp-servers` directory, you can run the service for production or development.

```bash
# path: ./mcp-servers
# Run the production container
docker compose up mcp_server_stability

# Run the development container with hot-reloading
docker compose -f docker-compose.debug.yml up mcp_server_stability
```

### Locally

```bash
# path: ./mcp-servers/mcp-server-stability/
# Basic run
uv run python -m mcp_server_stability

# Or with custom port and host
uv run python -m mcp_server_stability --port 8000 --reload
```

### Using Docker (Standalone)

```bash
# path: ./mcp-servers/mcp-server-stability/
# Build the image
docker build -t mcp-server-stability .

# Run the container
docker run --rm -it -p 8000:8000 --env-file .env mcp-server-stability
```

## Testing

```bash
# path: ./mcp-servers/mcp-server-stability/
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v
```

## Project Structure

```
mcp-server-stability/
├── src/
│   └── mcp_server_stability/
│       ├── __init__.py
│       ├── __main__.py              # Entry point (CLI + uvicorn)
│       ├── app.py                   # Application factory & lifespan
│       ├── logging_config.py        # Logging configuration
│       ├── schemas.py               # Pydantic request/response models
│       ├── x402_config.py           # x402 payment configuration
│       │
│       ├── api_routers/             # API-Only endpoints (REST)
│       │   ├── __init__.py
│       │   └── health.py            # Health check endpoint
│       │
│       ├── hybrid_routers/          # Hybrid endpoints (REST + MCP)
│       │   ├── __init__.py
│       │   └── pricing.py           # Pricing configuration endpoint
│       │
│       ├── mcp_routers/             # MCP-Only endpoints
│       │   ├── __init__.py
│       │   └── generate_image.py    # Image generation tool
│       │
│       ├── middlewares/
│       │   ├── __init__.py
│       │   └── x402_wrapper.py      # x402 payment middleware
│       │
│       └── stable_diffusion/        # Business logic layer
│           ├── __init__.py
│           ├── config.py
│           └── module.py
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
