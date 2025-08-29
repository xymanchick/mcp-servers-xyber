# MCP Arxiv Server

> **General:** This repository provides an MCP (Model Context Protocol) server for searching and retrieving papers from the Arxiv preprint repository.

## Overview

This server exposes functionality to search Arxiv through the Model Context Protocol (MCP). It allows language models and AI agents to find and access academic papers.

## MCP Tools:

1. `arxiv_search`
    - **Description:** Searches Arxiv for papers, downloads their PDFs, and extracts the text content.
    - **Input:**
        - `query` (required): The search query.
        - `max_results` (optional): Maximum number of papers to return.
        - `max_text_length` (optional): Maximum number of characters of text to extract from each paper.
    - **Output:** A formatted string containing the title, authors, summary, and extracted text for each paper found.

## Requirements

- Python 3.12+
- UV (for dependency management)
- Docker (optional, for containerization)

## Setup

1. **Clone the Repository**:
   ```bash
   # path: /path/to/your/projects/
   git clone <repository-url>
   ```

2. **Create `.env` File based on `.env.example`**:
   Create a `.env` file inside `./mcp-server-arxiv/`.
   ```dotenv
   # Optional environment variables
   ARXIV_DEFAULT_MAX_RESULTS=5
   ARXIV_DEFAULT_MAX_TEXT_LENGTH=2000
   ```

3. **Install Dependencies**:
   ```bash
   # path: ./mcp-servers/mcp-server-arxiv/
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
docker compose up mcp_server_arxiv

# Run the development container with hot-reloading
docker compose -f docker-compose.debug.yml up mcp_server_arxiv
```

### Locally

```bash
# path: ./mcp-servers/mcp-server-arxiv/
# Basic run
uv run python -m mcp_server_arxiv

# Or with custom port and host
uv run python -m mcp_server_arxiv --port 8000 --reload
```

### Using Docker (Standalone)

```bash
# path: ./mcp-servers/mcp-server-arxiv/
# Build the image
docker build -t mcp-server-arxiv .

# Run the container
docker run --rm -it -p 8000:8000 --env-file .env mcp-server-arxiv
```

## Testing

```bash
# path: ./mcp-servers/mcp-server-arxiv/
# Run all tests
uv run pytest
```

## Project Structure

```
mcp-server-arxiv/
├── src/
│   └── mcp_server_arxiv/
        └── arxiv/
            ├── __init__.py
            ├── config.py
            ├── models.py
            ├── module.py
│       ├── __init__.py
│       ├── __main__.py
│       ├── logging_config.py
│       ├── server.py
├── tests/
│   ├── conftest.py
│   ├── test_module.py
│   └── test_server.py
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
