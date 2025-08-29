# MCP Stability Server

> **General:** This repository provides an MCP (Model Context Protocol) server for Stability AI image generation.
> It exposes an image generation tool via an MCP-compatible microservice.

## Overview

This server allows you to create a microservice that exposes Stability AI's image generation models through the Model Context Protocol (MCP).

## MCP Tools:

1. `generate_image`
    - **Description:** Generates an image from a text prompt using Stability AI.
    - **Input:**
        - `prompt` (required): A text description of the image to generate.
        - `negative_prompt` (optional): A text description of what to avoid in the image.
        - `aspect_ratio` (optional): The aspect ratio of the generated image (e.g., "16:9", "1:1").
        - `seed` (optional): A seed for reproducible generation.
        - `style_preset` (optional): A preset style to guide the generation (e.g., "photographic", "anime").
    - **Output:** The generated image as PNG bytes.

## Requirements

- Python 3.12+
- UV (for dependency management)
- Stability AI API Key
- Docker (optional, for containerization)

## Setup

1. **Clone the Repository**:
   ```bash
   # path: /path/to/your/projects/
   git clone <repository-url>
   ```

2. **Create `.env` File based on `.env.example`**:
   Create a `.env` file inside `./mcp-server-stability/`. You must provide your Stability AI API key.
   ```dotenv
   # Required environment variables
   STABILITY_API_KEY="your_stability_api_key"
   
   # Optional environment variables
   LOGGING_LEVEL="info"
   STABILITY_API_HOST="https://api.stability.ai"
   ```

3. **Install Dependencies**:
   ```bash
   # path: ./mcp-servers/mcp-server-stability/
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
```

## Project Structure

```
mcp-server-stability/
├── src/
│   └── mcp_server_stability/
│       └── stability/
│           ├── __init__.py
│           ├── config.py
│           └── module.py
│       ├── __init__.py
│       ├── __main__.py
│       ├── logging_config.py
│       ├── server.py
│       └── schemas.py
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
