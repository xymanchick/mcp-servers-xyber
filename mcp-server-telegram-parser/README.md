# MCP Telegram Parser Server

> **General:** This repository provides an MCP (Model Context Protocol) server for parsing recent messages from public Telegram channels using Telethon.
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
| `parse_telegram_channels` | **Free**   | Retrieves the last N messages from a list of public Telegram channels |

#### `parse_telegram_channels` Details:
- **Input:**
    - `channels` (required): A list of channel usernames (e.g., `["durov", "nytimes"]`).
    - `limit` (optional): The number of recent messages to fetch per channel (default: 10).
- **Output:** A structured result containing the messages from each channel, including text, date, views, and forwards.

*Note: Paid endpoints require x402 payment protocol configuration. See `env.example` for details.*

## API Documentation

This server automatically generates OpenAPI documentation. Once the server is running, you can access the interactive API docs at:

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs) (for REST endpoints)
- **MCP Inspector**: Use an MCP-compatible client to view available agent tools [http://localhost:8000/mcp](http://localhost:8000/mcp)

These interfaces allow you to explore all REST-accessible endpoints, view their schemas, and test them directly from your browser.

## Requirements

- **Python 3.12+**
- **UV** (for dependency management)
- **Telethon API credentials** (API ID and Hash from `my.telegram.org`)
- **A Telethon user session** (StringSession is recommended)
- **Docker** (optional, for containerization)

## Setup

1.  **Clone & Configure**
    ```bash
    git clone <repository-url>
    cd mcp-server-telegram-parser
    cp env.example .env
    # Configure your Telethon credentials (see .env.example).
    # Required: TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_STRING_SESSION
    ```

2.  **Virtual Environment**
    ```bash
    # working directory: ./mcp-servers/mcp-server-telegram-parser/
    uv sync
    ```

## Running the Server

### Using Docker Compose (Recommended)

From the root `mcp-servers` directory, you can run the service for production or development.

```bash
# path: ./mcp-servers
# Run the production container
docker compose up mcp_server_telegram_parser

# Run the development container with hot-reloading
docker compose -f docker-compose.debug.yml up mcp_server_telegram_parser
```

### Locally

```bash
# path: ./mcp-servers/mcp-server-telegram-parser/
# Basic run
uv run python -m mcp_server_telegram_parser

# Or with custom port and host
uv run python -m mcp_server_telegram_parser --port 8000 --reload
```

### Using Docker (Standalone)

```bash
# path: ./mcp-servers/mcp-server-telegram-parser/
# Build the image
docker build -t mcp-server-telegram-parser .

# Run the container
docker run --rm -it -p 8000:8000 --env-file .env mcp-server-telegram-parser
```

## Testing

```bash
# path: ./mcp-servers/mcp-server-telegram-parser/
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v
```

*Note: At the moment, there are no dedicated tests for this service.*

## Project Structure

```
mcp-server-telegram-parser/
├── src/
│   └── mcp_server_telegram_parser/
│       ├── __main__.py              # Entry point (CLI + uvicorn)
│       ├── app.py                   # Application factory & lifespan
│       ├── logging_config.py        # Logging configuration
│       ├── schemas.py               # Pydantic request/response models
│       ├── x402_config.py           # x402 payment configuration
│       │
│       ├── api_routers/             # API-Only endpoints (REST)
│       │   ├── __init__.py
│       │   └── health.py
│       │
│       ├── hybrid_routers/          # Hybrid endpoints (REST + MCP)
│       │   ├── __init__.py
│       │   └── pricing.py
│       │
│       ├── mcp_routers/             # MCP-Only endpoints
│       │   ├── __init__.py
│       │   └── parse_channels.py
│       │
│       ├── middlewares/             # x402 payment middleware
│       │   ├── __init__.py
│       │   └── x402_wrapper.py
│       │
│       └── telegram/                # Business logic layer
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

