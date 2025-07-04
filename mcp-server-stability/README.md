# MCP Stable Diffusion Server

> **General:** This repository provides an MCP (Model Context Protocol) server for Stable Diffusion image generation.
> It exposes an image generation tool via MCP-compatible microservice.

## Overview

This server demonstrates how to create a microservice that exposes Stable Diffusion image generation through the Model Context Protocol (MCP).

## MCP Tools:

1. `generate_image`
    - **Description:** Generates an image from a text prompt using Stable Diffusion
    - **Input:**
        - prompt (str)
        - negative_prompt (str, optional)
        - aspect_ratio (str, optional)
        - seed (int, optional)
        - output_format (str, optional)
    - **Output:** Image bytes (PNG/JPG)

## Requirements

- Python 3.12+
- UV (for dependency management)
- Docker (optional, for containerization)

## Setup

1. **Clone the Repository**:
   ```bash
   git clone <repository-url>
   cd mcp-server-stable-diffusion
   ```

2. **Create `.env` File**:
   ```dotenv
   # Example environment variables
   MCP_STABLE_DIFFUSION_HOST="0.0.0.0"
   MCP_STABLE_DIFFUSION_PORT=8000
   LOGGING_LEVEL="info"
   STABLE_DIFFUSION_URL="https://api.stability.ai/v2beta/stable-image/generate/core"
   STABLE_DIFFUSION_API_KEY="your_api_key"
   ```

3. **Install Dependencies**:
   ```bash
   uv sync .
   ```

## Running the Server

### Locally

```bash
python -m mcp_server_calculator
```

### Using Docker

```bash
# Build the image
docker build -t mcp-server-stable-diffusion .

# Run the container
docker run --rm -it -p 8000:8000 --env-file .env mcp-server-stable-diffusion
```

## Example Client
When server startup is completed, any MCP client
can utilize connection to it

This example shows how to use the stable diffusion service with a LangGraph ReAct agent:

```python
import os
import asyncio
from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI

async def main():
    load_dotenv()
    model = ChatOpenAI(model="gpt-4")
    client = MultiServerMCPClient({
        "image-generation": {
            "url": "https://localhost:8000",
            "transport": "streamable_http",
        }
    })
    tools = await client.get_tools()
    for tool in tools:
        tool.return_direct = True
    agent = create_react_agent(model, tools)
    response = await agent.ainvoke({
        "messages": [{
            "role": "user",
            "content": "Generate a photo of a futuristic city at sunset."
        }]
    })
    print(response["messages"][-1].content)

if __name__ == "__main__":
    asyncio.run(main())
```

## Project Structure

```
mcp-server-stable-diffusion/
├── src/
│   └── mcp_server_calculator/
│       └── stable_diffusion/ # Contains all the business logic
│           ├── __init__.py # Exposes all needed functionality to server.py
│           ├── config.py # Contains module env settings, custom Error classes
│           ├── client.py # Business module core logic
│       ├── __init__.py
│       ├── __main__.py # Contains uvicorn server setup logic
│       ├── logging_config.py # Contains shared logging configuration
│       ├── server.py # Contains tool schemas/definitions, sets MCP server up
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
