# MCP YouTube Server

> **General:** This repository implements an MCP (Model Context Protocol) server for YouTube search and transcript retrieval.

## Overview

This project provides a microservice that exposes YouTube video searching and transcript retrieval through the Model Context Protocol (MCP). It uses the YouTube Data API v3 for searching and the `youtube-transcript-api` library for fetching transcripts.

## MCP Tools:

1.  `youtube_search_and_transcript`
    - **Description:** Searches YouTube for videos and retrieves their transcripts.
    - **Input:**
        - `query` (required): The search query for YouTube videos.
        - `max_results` (optional): The maximum number of videos to return (default: 5).
        - `transcript_language` (optional): The desired language for the transcript (e.g., "en").
        - `published_after` (optional): Filters for videos published after a specific date (ISO 8601).
        - `published_before` (optional): Filters for videos published before a specific date (ISO 8601).
        - `order_by` (optional): The sorting order for the results (e.g., "relevance", "date").
    - **Output:** A formatted string containing video details and their transcripts.

## Requirements

- Python 3.12+
- UV (for dependency management)
- YouTube Data API Key
- Docker (optional, for containerization)

## Setup

1.  **Clone the Repository**:
    ```bash
    # path: /path/to/your/projects/
    git clone <repository-url>
    ```

2.  **Create `.env` File based on `.env.example`**:
    Create a `.env` file inside `./mcp-server-youtube/`. You must provide your YouTube Data API key.
    ```dotenv
    # Required environment variables
    YOUTUBE_API_KEY="your_youtube_api_key"
    
    # Optional environment variables
    LOGGING_LEVEL="info"
    ```

3.  **Install Dependencies**:
    ```bash
    # path: ./mcp-servers/mcp-server-youtube/
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
docker compose up mcp_server_youtube

# Run the development container with hot-reloading
docker compose -f docker-compose.debug.yml up mcp_server_youtube
```

### Locally

```bash
# path: ./mcp-servers/mcp-server-youtube/
# Basic run
uv run python -m mcp_server_youtube

# Or with custom port and host
uv run python -m mcp_server_youtube --port 8000 --reload
```

### Using Docker (Standalone)

```bash
# path: ./mcp-servers/mcp-server-youtube/
# Build the image
docker build -t mcp-server-youtube .

# Run the container
docker run --rm -it -p 8000:8000 --env-file .env mcp-server-youtube
```

## Testing

```bash
# path: ./mcp-servers/mcp-server-youtube/
# Run all tests
uv run pytest
```

## Project Structure

```
mcp-server-youtube/
├── src/
│   └── mcp_server_youtube/
│       └── youtube/
│           ├── __init__.py
│           ├── config.py
│           └── module.py
│       ├── __init__.py
│       ├── __main__.py
│       ├── logging_config.py
│       └── server.py
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

1.  Fork the repository
2.  Create your feature branch
3.  Commit your changes
4.  Push to the branch
5.  Create a Pull Request

## License

MIT
