# MCP Cartesia Server

> **General:** This repository provides an MCP (Model Context Protocol) server for text-to-speech (TTS) synthesis using the Cartesia API.

## Overview

This server exposes functionality to generate speech from text through the Model Context Protocol (MCP). It allows language models and AI agents to create audio from text inputs.

## MCP Tools:

1. `generate_cartesia_tts`
    - **Description:** Synthesizes speech from the provided text using a specified voice and model, then saves it as a WAV file.
    - **Input:**
        - `text` (required): The text to be converted to speech.
        - `voice_id` (optional): The ID of the voice to use for the synthesis.
        - `model_id` (optional): The ID of the TTS model to use.
    - **Output:** The file path to the generated WAV audio file.

## Requirements

- Python 3.12+
- UV (for dependency management)
- Cartesia API Key
- Docker (optional, for containerization)

## Setup

1. **Clone the Repository**:
   ```bash
   # path: /path/to/your/projects/
   git clone <repository-url>
   ```

2. **Create `.env` File based on `.env.example`**:
   Create a `.env` file inside `./mcp-server-cartesia/`. You must provide your Cartesia API key.
   ```dotenv
   # Required environment variables
   CARTESIA_API_KEY="your_cartesia_api_key"
   
   # Optional environment variables
   CARTESIA_VOICE_ID="your_default_voice_id"
   CARTESIA_MODEL_ID="your_default_model_id"
   ```

3. **Install Dependencies**:
   ```bash
   # path: ./mcp-servers/mcp-server-cartesia/
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
docker compose up mcp_server_cartesia

# Run the development container with hot-reloading
docker compose -f docker-compose.debug.yml up mcp_server_cartesia
```

### Locally

```bash
# path: ./mcp-servers/mcp-server-cartesia/
# Basic run
uv run python -m mcp_server_cartesia

# Or with custom port and host
uv run python -m mcp_server_cartesia --port 8000 --reload
```

### Using Docker (Standalone)

```bash
# path: ./mcp-servers/mcp-server-cartesia/
# Build the image
docker build -t mcp-server-cartesia .

# Run the container
docker run --rm -it -p 8000:8000 --env-file .env mcp-server-cartesia
```

## Testing

```bash
# path: ./mcp-servers/mcp-server-cartesia/
# Run all tests
uv run pytest
```

## Project Structure

```
mcp-server-cartesia/
├── src/
│   └── mcp_server_cartesia/
        └── cartesia/
            ├── __init__.py
            ├── config.py
            ├── module.py
│       ├── __init__.py
│       ├── __main__.py
│       ├── logging_config.py
│       ├── server.py
├── tests/
│   ├── conftest.py
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
