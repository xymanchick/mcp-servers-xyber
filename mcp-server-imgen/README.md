# MCP Image Generation Service

> **Note:** This service is part of the unified `mcp-servers` repository.
> It is recommended to build and run this service using the top-level Dockerfile
> located in the root of the `mcp-servers` repository.
> See the [main README](../../README.md) for instructions.

This service provides an MCP-compatible server that generates images based on text prompts using Google Vertex AI.

## Features

*   Accepts text prompts and image dimension parameters.
*   Utilizes Google Vertex AI's FLUX-dev model (or configured equivalent).
*   Returns generated images encoded in base64.

## Environment Variables

This service requires Google Cloud credentials and project information, typically provided via environment variables. See the top-level `.env.example` file in the `mcp-servers` root directory for the full list.

Key variables include:

*   `GOOGLE_PROJECT_ID`
*   `GOOGLE_LOCATION`
*   `GOOGLE_ENDPOINT_ID`
*   `GOOGLE_API_ENDPOINT`
*   Google Credentials (structured as `GOOGLE_CREDENTIALS_*` variables)

## API

The server exposes the standard MCP `list_tools` and `call_tool` endpoints.

*   **Tool Name:** `generate_image`
*   **Input Schema:** `ImageGenerationRequest` (includes `prompt`, `width`, `height`, `num_images`, etc.)
*   **Output:** List containing a `TextContent` confirmation and one or more `ImageContent` objects with base64 PNG data.

## Running Locally (Development Only)

While Docker is the recommended method, you can run locally for development:

1.  **Navigate to the `mcp-servers` root directory.**
2.  **Ensure `uv` is installed.**
3.  **(Optional) Create and activate a virtual environment:**
    ```bash
    uv venv
    source .venv/bin/activate # Or .venv\Scripts\activate on Windows
    ```
4.  **Install dependencies (from the root):**
    ```bash
    uv sync
    ```
5.  **Set environment variables:** Export the required `GOOGLE_*` variables from your `.env` file.
6.  **Run the service:**
    ```bash
    # Note: This runs the service directly, bypassing the top-level CMD logic.
    # Ensure argparse default in __main__ is 8001 if running this way
    python -m mcp_server_imgen --port 8001
    ```
    *(The `--reload` flag is useful for development)*
    ###
   
