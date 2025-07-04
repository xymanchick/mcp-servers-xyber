# MCP Server Cartesia

A microservice for the MCP (Multimodal Context Platform) that provides text-to-speech capabilities using the Cartesia TTS engine.

## Features

- Text to speech conversion via Cartesia TTS
- Audio file output
- Integration with the MCP platform

## Installation

This service is designed to run as a Docker container.

## Usage

The server exposes an API endpoint for text-to-speech conversion.

## Development

See pyproject.toml for dependencies and build information.

## Overview

This server provides an MCP (Model Context Protocol) interface with a single tool to synthesize speech from text using the Cartesia API. It saves the generated audio as a WAV file and returns the path to the file.

## Features

-   Generates speech from text using Cartesia TTS.
-   Configurable voice ID and model ID.
-   Saves audio output as WAV files.
-   MCP-compliant API endpoints (`list_tools`, `call_tool`).
-   Uses SSE (Server-Sent Events) transport.
-   Docker support for easy deployment.

## Requirements

-   Python 3.11+
-   Cartesia API Key
-   `uv` (recommended for dependency management) or `pip`

## Setup

1.  **Clone the repository** (or place these files within your `mcp-servers` structure).
2.  **Create Environment File:**
    Create a `.env` file in this directory (`mcp-server-cartesia`) based on `.env.example`. Add your `CARTESIA_API_KEY`. You can optionally override default `CARTESIA_VOICE_ID` and `CARTESIA_MODEL_ID`.
3.  **Install Dependencies:**
    It's recommended to use a virtual environment. Navigate to the `mcp-server-cartesia` directory.

    ```bash
    # Using uv (recommended)
    uv venv
    source .venv/bin/activate  # or .venv\Scripts\activate on Windows
    uv pip install -e .[dev] # Install in editable mode with dev tools

    # Using pip + venv
    # python -m venv .venv
    # source .venv/bin/activate # or .venv\Scripts\activate on Windows
    # pip install -e .[dev]
    ```

## Running the Server

Ensure your virtual environment is activated and the `.env` file is present.

```bash
# Run with default host (0.0.0.0) and port (8003)
python -m mcp_server_cartesia

# Run on a specific host/port
python -m mcp_server_cartesia --host 127.0.0.1 --port 8003
```

Or using Docker:

```bash
docker build -t mcp-server-cartesia .
docker run --rm -it -p 8003:8003 --env-file .env mcp-server-cartesia
