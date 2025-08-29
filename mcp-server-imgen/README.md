# MCP Image Generation Server

> **General:** This repository provides an MCP (Model Context Protocol) server for generating images from text prompts using Google Vertex AI.

## Overview

This server allows language models and AI agents to create images by providing a descriptive text prompt. It uses Google Vertex AI's image generation models and returns the resulting images encoded in base64.

## MCP Tools:

1. `generate_image`
    - **Description:** Generates one or more images based on a text prompt.
    - **Input:**
        - `prompt` (required): A text description of the image to generate.
        - `height` (optional): The height of the image in pixels.
        - `width` (optional): The width of the image in pixels.
        - `num_images` (optional): The number of images to generate.
    - **Output:** A list of base64-encoded PNG images.

## Requirements

- Python 3.12+
- UV (for dependency management)
- Google Cloud Platform (GCP) project and credentials
- Docker (optional, for containerization)

## Setup

1. **Clone the Repository**:
   ```bash
   # path: /path/to/your/projects/
   git clone <repository-url>
   ```

2. **Create `.env` File based on `.env.example`**:
   Create a `.env` file inside `./mcp-server-imgen/`. You must provide your Google Cloud project details and credentials.
   ```dotenv
   # Required Google Cloud environment variables
   GOOGLE_PROJECT_ID="your-gcp-project-id"
   GOOGLE_LOCATION="your-gcp-region"
   # ... and other GOOGLE_ credentials as specified in .env.example
   ```

3. **Install Dependencies**:
   ```bash
   # path: ./mcp-servers/mcp-server-imgen/
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
docker compose up mcp_server_imgen

# Run the development container with hot-reloading
docker compose -f docker-compose.debug.yml up mcp_server_imgen
```

### Locally

```bash
# path: ./mcp-servers/mcp-server-imgen/
# Basic run
uv run python -m mcp_server_imgen

# Or with custom port and host
uv run python -m mcp_server_imgen --port 8000 --reload
```

### Using Docker (Standalone)

```bash
# path: ./mcp-servers/mcp-server-imgen/
# Build the image
docker build -t mcp-server-imgen .

# Run the container
docker run --rm -it -p 8000:8000 --env-file .env mcp-server-imgen
```

## Testing

```bash
# path: ./mcp-servers/mcp-server-imgen/
# Run all tests
uv run pytest
```

## Project Structure

```
mcp-server-imgen/
├── src/
│   └── mcp_server_imgen/
│       ├── imgen/
│       │   ├── __init__.py
│       │   ├── config.py
│       │   └── module.py
│       ├── __init__.py
│       ├── __main__.py
│       ├── logging_config.py
│       └── server.py
├── tests/
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
