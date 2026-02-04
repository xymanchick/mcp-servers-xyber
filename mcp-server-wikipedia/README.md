# MCP Wikipedia Server

> **General:** This repository implements an MCP (Model Context Protocol) server for Wikipedia search and content retrieval functionality.

## Overview

This project provides a microservice that exposes comprehensive Wikipedia functionality through the Model Context Protocol (MCP). It uses the `wikipedia-api` library to search, retrieve, and process Wikipedia articles, making it easy to integrate Wikipedia content into AI applications and multi-tool agent systems.

## MCP Tools:

1.  `search_wikipedia`
    - **Description:** Searches for articles and returns a list of titles.
    - **Input:** `query` (required), `limit` (optional).

2.  `get_article`
    - **Description:** Retrieves the full content of an article.
    - **Input:** `title` (required).

3.  `get_summary`
    - **Description:** Fetches the summary of an article.
    - **Input:** `title` (required).

4.  `get_sections`
    - **Description:** Lists all section titles in an article.
    - **Input:** `title` (required).

5.  `get_links`
    - **Description:** Lists all internal links within an article.
    - **Input:** `title` (required).

6.  `get_related_topics`
    - **Description:** Finds related topics based on an article's links.
    - **Input:** `title` (required), `limit` (optional).

## Requirements

- Python 3.12+
- UV (for dependency management)
- Docker (optional, for containerization)

## Setup

1.  **Clone the Repository**:
    ```bash
    # path: /path/to/your/projects/
    git clone <repository-url>
    ```

2.  **Create `.env` File (Optional)**:
    Create a `.env` file inside `./mcp-server-wikipedia/`. It is highly recommended to set a descriptive `WIKIPEDIA_USER_AGENT`.
    ```dotenv
    # Optional environment variables
    WIKIPEDIA_USER_AGENT="MyCoolAgent/1.0 (https://example.com; my-email@example.com)"
    WIKIPEDIA_LANGUAGE="en"
    LOGGING_LEVEL="info"
    ```

3.  **Install Dependencies**:
    ```bash
    # path: ./mcp-servers/mcp-server-wikipedia/
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
docker compose up mcp_server_wikipedia

# Run the development container with hot-reloading
docker compose -f docker-compose.debug.yml up mcp_server_wikipedia
```

### Locally

```bash
# path: ./mcp-servers/mcp-server-wikipedia/
# Basic run
uv run python -m mcp_server_wikipedia

# Or with custom port and host
uv run python -m mcp_server_wikipedia --port 8000 --reload
```

### Using Docker (Standalone)

```bash
# path: ./mcp-servers/mcp-server-wikipedia/
# Build the image
docker build -t mcp-server-wikipedia .

# Run the container
docker run --rm -it -p 8000:8000 --env-file .env mcp-server-wikipedia
```

## Testing

```bash
# path: ./mcp-servers/mcp-server-wikipedia/
# Run all tests
uv run pytest
```

## Project Structure

```
mcp-server-wikipedia/
├── src/
│   └── mcp_server_wikipedia/
│       ├── __init__.py
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
│       │   ├── search.py
│       │   ├── article.py
│       │   ├── summary.py
│       │   ├── sections.py
│       │   ├── links.py
│       │   └── related.py
│       │
│       ├── middlewares/             # x402 payment middleware
│       │   ├── __init__.py
│       │   └── x402_wrapper.py
│       │
│       └── wikipedia/               # Business logic layer
│           ├── __init__.py
│           ├── config.py
│           ├── models.py
│           └── module.py
│
├── tests/
├── .gitignore
├── Dockerfile
├── pyproject.toml
├── README.md
└── uv.lock
```

## Contributing

1.  Fork the repository
2.  Create your feature branch
3.  Commit your changes
4.  Push to the branch
5.  Create a Pull Request

## License

This project is licensed under the MIT License.
