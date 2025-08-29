# MCP Server - Tavily Web Search

> **General:** This repository provides an MCP (Model Context Protocol) server implementation for interacting with the Tavily AI web search API.

## Overview

This project implements a microservice that exposes Tavily web search functionality through the Model Context Protocol (MCP). It uses the `langchain-tavily` library to interact with the Tavily Search API.

## MCP Tools:

1. `tavily_web_search`
    - **Description:** Performs a web search using the Tavily API based on the provided query.
    - **Input:**
        - `query` (required): The search query.
        - `max_results` (optional): Maximum number of results to return.
    - **Output:** A string containing formatted search results, including titles, URLs, and snippets of content.

## Requirements

- Python 3.12+
- UV (for dependency management)
- Tavily AI API Key
- Docker (optional, for containerization)

## Setup

1. **Clone the Repository**:
   ```bash
   # path: /path/to/your/projects/
   git clone <repository-url>
   ```

2. **Create `.env` File based on `.env.example`**:
   Create a `.env` file inside `./mcp-server-tavily/`. You must provide your Tavily API key.
   ```dotenv
   # Required environment variables
   TAVILY_API_KEY="your_tavily_api_key"
   
   # Optional environment variables
   LOGGING_LEVEL="info"
   ```

3. **Install Dependencies**:
   ```bash
   # path: ./mcp-servers/mcp-server-tavily/
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
```

## Project Structure

```
mcp-server-tavily/
├── src/
│   └── mcp_server_tavily/
│       └── tavily/
│           ├── __init__.py
│           ├── config.py
│           └── module.py
│       ├── __init__.py
│       ├── __main__.py
│       ├── logging_config.py
│       └── server.py
├── .env.example
├── .gitignore
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

MIT
