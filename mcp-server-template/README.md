# MCP Weather Server

> **General:** This repository serves as a template for creating new MCP (Model Context Protocol) servers.
> It provides a weather service implementation with best practices for MCP-compatible microservices.

## Overview

This template demonstrates how to create a microservice that exposes functionality through the Model Context Protocol (MCP). It includes a weather service that retrieves data from the OpenWeatherMap API.

## MCP Tools:

1. `get_weather`
    - **Description:** Retrieves current weather information for a location.
    - **Input:**
        - `latitude` (optional): Location latitude.
        - `longitude` (optional): Location longitude.
        - `units` (optional): Unit system (metric or imperial).
    - **Output:** A dictionary containing weather state, temperature, and humidity.

## Requirements

- Python 3.12+
- UV (for dependency management)
- OpenWeatherMap API key
- Docker (optional, for containerization)

## Setup

1. **Clone the Repository**:
   ```bash
   # path: /path/to/your/projects/
   git clone <repository-url>
   ```

2. **Create `.env` File based on `.env.example`**:
   Create a `.env` file inside `./mcp-server-template/`.
   ```dotenv
   # Required environment variables
   WEATHER_API_KEY="your_openweathermap_api_key"
   
   # Optional environment variables
   WEATHER_TIMEOUT_SECONDS=10
   WEATHER_ENABLE_CACHING=true
   WEATHER_CACHE_TTL_SECONDS=300
   ```

3. **Install Dependencies**:
   ```bash
   # path: ./mcp-servers/mcp-server-template/
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
docker compose up mcp_server_weather

# Run the development container with hot-reloading
docker compose -f docker-compose.debug.yml up mcp_server_weather
```

### Locally

```bash
# path: ./mcp-servers/mcp-server-template/
# Basic run
uv run python -m mcp_server_weather

# Or with custom port and host
uv run python -m mcp_server_weather --port 8000 --reload
```

### Using Docker (Standalone)

```bash
# path: ./mcp-servers/mcp-server-template/
# Build the image
docker build -t mcp-server-weather .

# Run the container
docker run --rm -it -p 8000:8000 --env-file .env mcp-server-weather
```

## Testing

```bash
# path: ./mcp-servers/mcp-server-template/
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v
```

## Project Structure

```
mcp-server-weather/
├── src/
│   └── mcp_server_weather/
        └── weather/
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
│   ├── test_retry_logic.py
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
