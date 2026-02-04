# MCP Server for Qdrant Vector Database

> **General:** This repository provides an MCP (Model Context Protocol) server for Qdrant vector database integration.
> It enables AI agents to perform semantic search, store documents, and manage collections with advanced multi-tenant filtering capabilities.

## Overview

This MCP server exposes Qdrant vector database functionality through the Model Context Protocol. It includes advanced features like multi-tenant data isolation, configurable payload indexes, and optimized HNSW settings for high-performance semantic search.

## MCP Tools:

1. `qdrant_store`
    - **Description:** Store information with metadata in Qdrant collections.
    - **Input:**
        - `information` (required): The information to store.
        - `collection_name` (required): The name of the collection.
        - `metadata` (optional): JSON metadata to store with the information.
    - **Output:** A confirmation string with storage details.

2. `qdrant_find`
    - **Description:** Search documents with semantic similarity and optional filtering.
    - **Input:**
        - `query` (required): The search query.
        - `collection_name` (required): The name of the collection to search.
        - `search_limit` (optional): Maximum number of results (default: 10).
        - `filters` (optional): Optional filters as field_path -> value pairs.
    - **Output:** A list of scored points with content and metadata.

3. `qdrant_get_collections`
    - **Description:** List all available collections.
    - **Input:** None
    - **Output:** A list of collection names.

4. `qdrant_get_collection_info`
    - **Description:** Get detailed collection configuration including payload schema.
    - **Input:**
        - `collection_name` (required): The name of the collection.
    - **Output:** Collection information with configuration details.

## Requirements

- Python 3.12+
- UV (for dependency management)
- Docker (optional, for containerization)
- Qdrant instance (local or cloud)

## Setup

1. **Clone the Repository**:
   ```bash
   # path: /path/to/your/projects/
   git clone <repository-url>
   ```

2. **Create `.env` File based on `.env.example`**:
   Create a `.env` file inside `./mcp-server-qdrant/`.
   ```dotenv
   # Basic Connection
   QDRANT_HOST=localhost
   QDRANT_PORT=6333
   QDRANT_API_KEY="your_api_key"

   # Embedding Configuration
   EMBEDDING_PROVIDER=fastembed
   EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
   ```

3. **Install Dependencies**:
   ```bash
   # path: ./mcp-servers/mcp-server-qdrant/
   # Using UV (recommended)
   uv sync
   
   # Or install for development
   uv sync --group dev
   ```

## Running the Server

### Using Docker Compose (Recommended)

From the root `mcp-servers` directory, you can run the service for production or development.

```bash
# path: ./mcp-servers
# Run the production container
docker compose up mcp_server_qdrant

# Run the development container with hot-reloading
docker compose -f docker-compose.debug.yml up mcp_server_qdrant
```

### Locally

```bash
# path: ./mcp-servers/mcp-server-qdrant/
# Basic run
uv run python -m mcp_server_qdrant

# Or with custom port and host
uv run python -m mcp_server_qdrant --port 8000 --reload
```

### Using Docker (Standalone)

```bash
# path: ./mcp-servers/mcp-server-qdrant/
# Build the image
docker build -t mcp-server-qdrant .

# Run the container
docker run --rm -it -p 8000:8000 --env-file .env mcp-server-qdrant
```

## Testing

```bash
# path: ./mcp-servers/mcp-server-qdrant/
# Run all tests
uv run pytest
```

## Project Structure

```
mcp-server-qdrant/
├── src/
│   └── mcp_server_qdrant/
│       ├── __main__.py              # Entry point (CLI + uvicorn)
│       ├── app.py                   # Application factory & lifespan
│       ├── schemas.py               # Pydantic request/response models
│       ├── exceptions.py            # Custom exception definitions
│       ├── logging_config.py        # Logging configuration
│       ├── middleware.py            # Middleware configuration
│       ├── x402_config.py           # x402 payment configuration
│       ├── tools.py                 # Tool definitions
│       │
│       ├── api_routers/             # API-Only endpoints (REST)
│       │   ├── __init__.py
│       │   └── health.py            # Health check endpoint
│       │
│       ├── hybrid_routers/          # Hybrid endpoints (REST + MCP)
│       │   ├── __init__.py
│       │   └── pricing.py           # Pricing information
│       │
│       ├── mcp_routers/             # MCP-Only endpoints
│       │   ├── __init__.py
│       │   └── qdrant_tools.py      # Qdrant MCP tools
│       │
│       ├── middlewares/             # x402 payment middleware
│       │   ├── __init__.py
│       │   └── x402_wrapper.py
│       │
│       └── qdrant/                  # Business logic layer
│           ├── __init__.py
│           ├── config.py            # Qdrant configuration
│           ├── module.py            # Core Qdrant operations
│           └── embeddings/          # Embedding providers
│               ├── __init__.py
│               ├── base.py          # Base embedding interface
│               ├── factory.py       # Embedding factory
│               ├── fastembed.py     # FastEmbed implementation
│               └── types.py         # Type definitions
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
