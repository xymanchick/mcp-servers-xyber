# MCP PostgreSQL Server

> **General:** This repository provides an MCP (Model Context Protocol) server with tools to interact with a PostgreSQL database.

## Overview

This server allows language models and AI agents to query a PostgreSQL database. It provides a set of tools for retrieving information from the database tables.

## MCP Tools:

1. `get_character_by_name`
    - **Description:** Retrieves a character record from the database based on its unique name.
    - **Input:**
        - `name` (required): The name of the character to retrieve.
    - **Output:** A dictionary containing the character's data or an error message if not found.

## Requirements

- Python 3.12+
- UV (for dependency management)
- PostgreSQL database credentials
- Docker (optional, for containerization)

## Setup

1. **Clone the Repository**:
   ```bash
   # path: /path/to/your/projects/
   git clone <repository-url>
   ```

2. **Create `.env` File based on `.env.example`**:
   Create a `.env` file inside `./mcp-server-postgres/`. You must provide your PostgreSQL connection details.
   ```dotenv
   # Required PostgreSQL environment variables
   POSTGRES_HOST="your_db_host"
   POSTGRES_PORT=5432
   POSTGRES_USER="your_db_user"
   POSTGRES_PASSWORD="your_db_password"
   POSTGRES_DATABASE_NAME="your_db_name"
   ```

3. **Install Dependencies**:
   ```bash
   # path: ./mcp-servers/mcp-server-postgres/
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
docker compose up mcp_server_postgres

# Run the development container with hot-reloading
docker compose -f docker-compose.debug.yml up mcp_server_postgres
```

### Locally

```bash
# path: ./mcp-servers/mcp-server-postgres/
# Basic run
uv run python -m mcp_server_postgres

# Or with custom port and host
uv run python -m mcp_server_postgres --port 8000 --reload
```

### Using Docker (Standalone)

```bash
# path: ./mcp-servers/mcp-server-postgres/
# Build the image
docker build -t mcp-server-postgres .

# Run the container
docker run --rm -it -p 8000:8000 --env-file .env mcp-server-postgres
```

## Testing

```bash
# path: ./mcp-servers/mcp-server-postgres/
# Run all tests
uv run pytest
```

## Project Structure

```
mcp-server-postgres/
├── src/
│   ├── mcp_server_postgres/
│   │   ├── __init__.py
│   │   └── server.py
│   └── postgres_client/
│       ├── __init__.py
│       ├── client.py
│       ├── config.py
│       ├── database.py
│       └── models/
│           ├── __init__.py
│           ├── base_model.py
│           └── character_model.py
├── __main__.py
├── .env.example
├── .gitignore
├── Dockerfile
├── LICENSE
├── pyproject.toml
└── README.md
```

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT
