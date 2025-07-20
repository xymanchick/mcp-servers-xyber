# MCP Weather Server

> **General:** This repository serves as a template for creating new MCP (Model Context Protocol) servers.
> It provides a weather service implementation with best practices for MCP-compatible microservices.

## Overview

This template demonstrates how to create a microservice that exposes functionality through the Model Context Protocol (MCP). It includes a weather service that retrieves data from the OpenWeatherMap API.

## MCP Tools:

1. `get_weather`
    - **Description:** Retrieves current weather information for a location
    - **Input:**
        - latitude (optional): Location latitude
        - longitude (optional): Location longitude
        - units (optional): Unit system (metric or imperial)
    - **Output:** A dictionary containing weather state, temperature, and humidity

## Requirements

- Python 3.12+
- UV (for dependency management)
- OpenWeatherMap API key
- Docker (optional, for containerization)

## Setup

1. **Clone the Repository**:
   ```bash
   git clone <repository-url>
   cd mcp-server-weather
   ```

2. **Create `.env` File based on `.env.example`**:
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
   # Using UV (recommended)
   uv sync
   
   # Or install for development
   uv sync --group dev
   ```

## Running the Server

### Locally

```bash
# Basic run
uv run python -m mcp_server_weather

# Or with custom port and host
uv run python -m mcp_server_weather --port 8000 --reload
```

### Using Docker

```bash
# Build the image
docker build -t mcp-server-weather .

# Run the container
docker run --rm -it -p 8000:8000 --env-file .env mcp-server-weather
```

## Testing

Run the test suite using UV:

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run specific test files
uv run pytest tests/test_module.py tests/test_server.py

# Run with coverage
uv run pytest --cov=mcp_server_weather
```

## Example Client

When server startup is completed, any MCP client can utilize connection to it.

This example shows how to use the weather service with a LangGraph ReAct agent:

```python
import os
import asyncio
from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI

async def main():
    # Load environment variables from .env, should contain OPENAI_API_KEY
    load_dotenv()

    # Initialize LLM
    model = ChatOpenAI(model="gpt-4")

    # Connect to MCP server
    client = MultiServerMCPClient(
        {
        "weather-service": {
            "url": "https://localhost:8000",
            "transport": "streamable_http",}
        }
    )

    # !! IMPORTANT : Get tools and modify them to have return_direct=True!!!
    # Otherwise langgraph agent could fall in an eternal loop,
    # ignoring tool results
    tools: list[StructuredTool] = await client.get_tools()
    for tool in tools:
        tool.return_direct = True

    # Use case 1: Create agent with tools
    agent = create_react_agent(model, tools)

    # Example query using the weather service
    response = await agent.ainvoke({
        "messages": [{
            "role": "user",
            "content": "What's the current weather in London?"
        }]
    })

    print(response["messages"][-1].content)

if __name__ == "__main__":
    asyncio.run(main())
```

## Project Structure

```
mcp-server-weather/
├── src/
│   └── mcp_server_weather/
        └── weather/ # Contains all the business logic
            ├── __init__.py # Exposes all needed functionality to server.py
            ├── config.py # Contains module env settings, custom Error classes
            ├── models.py # Data models for weather information
            ├── module.py # Business module core logic
│       ├── __init__.py
│       ├── __main__.py # Contains uvicorn server setup logic
│       ├── logging_config.py # Contains shared logging configuration
│       ├── server.py # Contains tool schemas/definitions, sets MCP server up
├── tests/
│   ├── conftest.py # Common test fixtures
│   ├── test_module.py # Tests for the weather client
│   ├── test_retry_logic.py # Tests for retry mechanism
│   └── test_server.py # Tests for MCP server
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
