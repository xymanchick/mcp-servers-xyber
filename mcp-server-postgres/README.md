# MCP Server - PostgreSQL Tools

This service provides an MCP-compliant server interface with tools to interact with a configured PostgreSQL database. It uses the `mcp` library framework and includes the `postgres_client` module for database interactions.

## Setup

1.  **Create Environment File:**
    Create a `.env` file in this directory (`mcp-server-postgres`) and fill in your PostgreSQL connection details. You can use `.env.example` as a template.

    ```dotenv
    # .env
    POSTGRES_HOST=your_db_host
    POSTGRES_PORT=5432
    POSTGRES_USER=your_db_user
    POSTGRES_PASSWORD=your_db_password
    POSTGRES_DATABASE_NAME=your_db_name

    # Optional MCP server settings (used by __main__.py)
    MCP_POSTGRES_HOST=0.0.0.0 # Host for the server process
    MCP_POSTGRES_PORT=8000    # Port for the server process
    MCP_POSTGRES_RELOAD=false # Enable Uvicorn auto-reload
    MCP_POSTGRES_LOG_LEVEL=info # Log level for Uvicorn
    ```

2.  **Install Dependencies:**
    It's recommended to use a virtual environment.
    Navigate to the `mcp-server-postgres` directory in your terminal.

    ```bash
    # Using uv (recommended)
    uv venv
    source .venv/bin/activate  # or .venv\Scripts\activate on Windows
    # Install the project in editable mode, including dev dependencies
    uv pip install -e .[dev]

    # Using pip + venv
    # python -m venv .venv
    # source .venv/bin/activate # or .venv\Scripts\activate on Windows
    # pip install -e .[dev]
    ```
    *Note: The `-e .` command installs the current project (`mcp-server-postgres`) in editable mode. Due to the `pyproject.toml` configuration (`tool.hatch.build.sources`), this makes both the `mcp_server_postgres` package (containing `server.py`) and the `postgres_client` package (containing database logic) available for import.*

3.  **Run the Server:**
    Ensure your virtual environment is activated.
    The server reads host/port from command-line arguments (or defaults) and reload/log settings from environment variables.

    ```bash
    # Run with default host (0.0.0.0) and port (8000)
    python -m mcp_server_postgres

    # Run on a specific host/port
    python -m mcp_server_postgres --host 127.0.0.1 --port 8001
    ```
    For development with auto-reload (reads `MCP_POSTGRES_RELOAD` from `.env` or environment):
    ```bash
    # Ensure MCP_POSTGRES_RELOAD=true is set in .env or exported
    python -m mcp_server_postgres
    ```

## Usage

This server follows the MCP protocol. Communication typically happens via Server-Sent Events (SSE) on the `/sse` endpoint and message posting on `/messages/`, managed by the Starlette wrapper in `__main__.py`.

Refer to the MCP documentation for client interaction details.

**Available Tools (via `list_tools`):**

*   `get_character_by_name`:
    *   Description: Retrieves a character record from the database based on its unique name.
    *   Input Schema: `GetCharacterByNameRequest` (`{"name": "string"}`)
    *   Output: `CharacterResponse` object or `TextContent` error/not found message.

*Note: Direct HTTP access to tool endpoints is replaced by the MCP `call_tool` mechanism.*

## Development

*   **Linting/Formatting:** Use `ruff`, `black`, and `isort` (configured in `pyproject.toml`). Install dev dependencies (`uv pip install -e .[dev]`) and run:
    ```bash
    ruff format .
    ruff check . --fix
    ```
*   **Testing:** Run tests using `pytest` (requires dev dependencies).
*   **Dependencies:** Key dependencies include `mcp`, `starlette`, `uvicorn`, `sqlalchemy`, `asyncpg`, `pydantic-settings`, `python-dotenv`.

## Project Structure

```
 mcp-server-postgres/
 ├── mcp_server_postgres/      # Main application package (MCP server logic)
 │   ├── __init__.py
 │   └── server.py           # MCP Server definition, tools, lifespan
 ├── postgres_client/        # PostgreSQL client logic package
 │   ├── __init__.py
 │   ├── client.py           # Service class for DB operations (_PostgresService)
 │   ├── config.py           # Pydantic configuration (PostgresConfig)
 │   ├── database.py         # SQLAlchemy engine/session setup
 │   └── models/             # SQLAlchemy models
 │       ├── __init__.py
 │       ├── base_model.py   # Base for models
 │       └── character_model.py # Agent model
 ├── __main__.py             # Entry point (uvicorn + Starlette SSE wrapper)
 ├── .env.example            # Example environment variables
 ├── pyproject.toml          # Project metadata and dependencies (Hatch)
 └── README.md               # This file
```
