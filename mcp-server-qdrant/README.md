# MCP Server for Qdrant Vector Database

> **General:** This repository provides an MCP (Model Context Protocol) server for Qdrant vector database integration.
> It enables AI agents to perform semantic search, store documents, and manage collections with advanced multi-tenant filtering capabilities.

## Overview

This MCP server exposes Qdrant vector database functionality through the Model Context Protocol. It includes advanced features like multi-tenant data isolation, configurable payload indexes, and optimized HNSW settings for high-performance semantic search.

## MCP Tools:

1. `qdrant_store`
    - **Description:** Store information with metadata in Qdrant collections
    - **Input:**
      - request (dict): The request object containing:
          - information (string): The information to store
          - collection_name (string): The name of the collection
          - metadata (dict, optional): JSON metadata to store with the information
    - **Output:** A confirmation string with storage details

2. `qdrant_find`
    - **Description:** Search documents with semantic similarity and optional filtering
    - **Input:**
      - request (dict): The request object containing:
          - query (string): The search query
          - collection_name (string): The name of the collection to search
          - search_limit (int, default: 10): Maximum number of results
          - filters (dict, optional): Optional filters as field_path -> value pairs
    - **Output:** List of scored points with content and metadata

3. `qdrant_get_collections`
    - **Description:** List all available collections
    - **Input:** None
    - **Output:** List of collection names

4. `qdrant_get_collection_info`
    - **Description:** Get detailed collection configuration including payload schema
    - **Input:**
      - request (dict): The request object containing:
          - collection_name (string): The name of the collection
    - **Output:** Collection information with configuration details

## Requirements

- Python 3.12+
- UV (for dependency management)
- Docker (optional, for containerization)
- Qdrant instance (local or cloud)

## Setup

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/Xyber-Labs/mcp-servers
   cd mcp-servers/mcp-server-qdrant
   ```

2. **Create `.env` File based on `.env.example`**:
   ```dotenv
   # Basic Connection
   QDRANT_HOST=localhost
   QDRANT_PORT=6333
   QDRANT_API_KEY=your_api_key

   # Advanced: Multi-Tenant with Payload Indexes
   QDRANT_COLLECTION_CONFIG__HNSW_CONFIG__M=0
   QDRANT_COLLECTION_CONFIG__HNSW_CONFIG__PAYLOAD_M=16

   QDRANT_COLLECTION_CONFIG__PAYLOAD_INDEXES__0__FIELD_NAME=metadata.tenant_id
   QDRANT_COLLECTION_CONFIG__PAYLOAD_INDEXES__0__INDEX_TYPE=keyword
   QDRANT_COLLECTION_CONFIG__PAYLOAD_INDEXES__0__IS_TENANT=true

   QDRANT_COLLECTION_CONFIG__PAYLOAD_INDEXES__1__FIELD_NAME=metadata.user_id
   QDRANT_COLLECTION_CONFIG__PAYLOAD_INDEXES__1__INDEX_TYPE=keyword

   # Embedding Configuration
   EMBEDDING_PROVIDER=fastembed
   EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
   ```

3. **Install Dependencies**:
   ```bash
   uv sync .
   ```

## Running the Server

### Locally

```bash
# Basic run
python -m mcp_server_qdrant

# Custom port and host
python -m mcp_server_qdrant --host 0.0.0.0 --port 8000
```

### Using Docker (Advanced/Standalone)

```bash
# Build the image
docker build -t mcp-server-qdrant .

# Run the container
docker run --rm -p 8005:8000 --env-file .env mcp-server-qdrant
```

### Using Docker Compose (Recommended)

The recommended way to run this service is as part of the full `mcp-servers` monorepo. The repository root contains both `docker-compose.yml` and `docker-compose.debug.yml` for orchestrating all services, including Qdrant and its persistent storage.

**Clone the entire repository:**
```bash
git clone https://github.com/Xyber-Labs/mcp-servers
cd mcp-servers
```

**To launch only the Qdrant MCP service (and its dependencies) in normal mode:**
```bash
docker compose up --build mcp_server_qdrant
```

**To launch in debug mode (with hot reload and debugpy):**
```bash
docker compose -f docker-compose.debug.yml up --build mcp_server_qdrant
```

- The MCP Qdrant server will be available at [http://localhost:8005](http://localhost:8005) (or the port specified in the compose file)
- Qdrant's REST API will be available at [http://localhost:6333](http://localhost:6333)
- Qdrant's data is stored in the `qdrant-data` Docker volume (see compose files)

To stop and remove containers (but keep data):
```bash
docker compose down
```

To remove all data as well:
```bash
docker compose down -v
```

## Example Client

### With Cursor IDE

Add to your `~/.cursor/mcp.json`:
```json
{
  "servers": {
    "qdrant": {
      "url": "http://localhost:8005/mcp-server/mcp/"
    }
  }
}
```

### Programmatic Usage

```python
import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI

async def main():
    # Initialize LLM
    model = ChatOpenAI(model="gpt-4")

    # Connect to MCP server
    client = MultiServerMCPClient({
        "qdrant": {
            "url": "http://localhost:8005",
            "transport": "streamable_http"
        }
    })

    # Get tools and modify them to have return_direct=True
    tools = await client.get_tools()
    for tool in tools:
        tool.return_direct = True

    # Create agent with tools
    agent = create_react_agent(model, tools)

    # Example: Store and search documents
    response = await agent.ainvoke({
        "messages": [{
            "role": "user",
            "content": "Store information about machine learning and then search for it"
        }]
    })

    print(response["messages"][-1].content)

if __name__ == "__main__":
    asyncio.run(main())
```

## Project Structure

```
mcp-server-qdrant/
├── src/
│   └── mcp_server_qdrant/
│       └── qdrant/ # Contains all the business logic
│           ├── __init__.py # Exposes all needed functionality to server.py
│           ├── config.py # Contains module env settings, custom Error classes
│           ├── module.py # Business module core logic
│           └── embeddings/ # Embedding provider implementations
│               ├── __init__.py
│               ├── base.py
│               ├── factory.py
│               ├── fastembed.py
│               └── types.py
│       └── tests/ # Contains all the tests
│           ├── __init__.py
│           ├── conftest.py # Contains pytest fixtures
│           ├── test_middlewares.py # Contains tests for middlewares
│           └── test_validations.py # Contains tests for validations
│       ├── __init__.py
│       ├── __main__.py # Contains uvicorn server setup logic
│       ├── exceptions.py # Contains custom exceptions
│       ├── logging_config.py # Contains shared logging configuration
│       ├── middlewares.py # Contains custom middlewares
│       ├── server.py # Contains tool schemas/definitions, sets MCP server up
│       └── schemas.py # Contains Pydantic schemas for request/response validation
├── CONFIGURATION.md # Detailed configuration guide
├── .env.example
├── .gitignore
├── docker-compose.yml
├── Dockerfile
├── LICENSE
├── pyproject.toml
├── README.md
└── uv.lock
```

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

Apache License 2.0
