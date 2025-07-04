# MCP Wikipedia Server

> **General:** This repository implements an MCP (Model Context Protocol) server for Wikipedia search and content retrieval functionality. It allows language models or other agents to easily query Wikipedia content through a standardized protocol.

## Overview

This project provides a microservice that exposes comprehensive Wikipedia functionality through the Model Context Protocol (MCP). It uses the `wikipedia-api` library to search, retrieve, and process Wikipedia articles, making it easy to integrate Wikipedia content into AI applications and multi-tool agent systems.

---

## Features

- **6 Comprehensive Tools:** Complete set of Wikipedia operations including search, content retrieval, and navigation
- **Fast & Async:** Built with async I/O for high performance
- **Configurable:** Environment variables control language, user agent, and server settings
- **Docker Support:** Ready-to-use Dockerfile for containerized deployment
- **No API Key Required:** Wikipedia is free to use with proper user agent identification
- **Modern Python:** Requires Python 3.12+ with type hints and modern features

---

## MCP Tools

1. **`search_wikipedia`**
   - **Description:** Searches for articles matching a query and returns a list of titles
   - **Parameters:**
     - `query` (string, required): Search query string
     - `limit` (integer, optional, default: 10): Maximum number of results to return

2. **`get_article`**
   - **Description:** Retrieves the full content and metadata of an article by its exact title
   - **Parameters:**
     - `title` (string, required): Exact Wikipedia article title

3. **`get_summary`**
   - **Description:** Fetches just the summary/introduction of an article
   - **Parameters:**
     - `title` (string, required): Exact Wikipedia article title

4. **`get_sections`**
   - **Description:** Lists all section titles in an article
   - **Parameters:**
     - `title` (string, required): Exact Wikipedia article title

5. **`get_links`**
   - **Description:** Lists all internal links within an article
   - **Parameters:**
     - `title` (string, required): Exact Wikipedia article title

6. **`get_related_topics`**
   - **Description:** Finds related topics based on an article's internal links
   - **Parameters:**
     - `title` (string, required): Exact Wikipedia article title
     - `limit` (integer, optional, default: 20): Maximum number of related topics to return

---

## Project Structure

```
mcp-server-wikipedia/
├── src/
│   └── mcp_server_wikipedia/
│       ├── __init__.py
│       ├── __main__.py        # Entrypoint for running the server
│       ├── server.py          # Main MCP server, exposes tools, handles requests
│       ├── logging_config.py  # Logging setup
│       └── wikipedia/
│           ├── __init__.py
│           ├── config.py      # Configuration and settings
│           ├── models.py      # Data models and schemas
│           └── module.py      # Core Wikipedia API logic
├── .gitignore                 # Files/directories excluded from version control
├── Dockerfile                 # Containerization support
├── pyproject.toml            # Dependencies and build config
├── README.md
└── uv.lock                   # Lockfile for reproducible builds
```

---

## Requirements

- Python 3.12+
- No API key required (Wikipedia is free to use)
- [uv](https://github.com/astral-sh/uv) (recommended for dependency management)
- Docker (optional, for containerization)

---

## Setup

1. **Clone the Repository:**
   ```bash
   git clone <repository-url>
   cd mcp-server-wikipedia
   ```

2. **Create Environment File:**
   Create a `.env` file and customize the settings. It is highly recommended to set a descriptive `WIKIPEDIA_USER_AGENT`:
   ```dotenv
   # .env
   MCP_WIKIPEDIA_PORT=8006
   MCP_WIKIPEDIA_HOST=0.0.0.0
   WIKIPEDIA_USER_AGENT="MyCoolAgent/1.0 (https://example.com/my-agent; my-email@example.com)"
   WIKIPEDIA_LANGUAGE="en"
   LOGGING_LEVEL="info"
   ```

3. **Install Dependencies:**
   ```bash
   # Using uv (recommended)
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   uv sync

   # Or using pip + venv
   # python -m venv .venv
   # source .venv/bin/activate
   # pip install -e .[dev]
   ```

---

## Running the Server

Ensure your virtual environment is activated and the `.env` file is present and configured.

### Locally

```bash
# Run with default settings (uses port 8006 by default)
python -m mcp_server_wikipedia

# Run on a specific host/port
python -m mcp_server_wikipedia --host 127.0.0.1 --port 8007
```

### Using Docker

```bash
# Build the Docker image
docker build -t mcp-server-wikipedia .

# Run the container
docker run --rm -it -p 8006:8006 --env-file .env mcp-server-wikipedia
```

---

## API Usage

**Example tool call for searching:**
```json
{
  "name": "search_wikipedia",
  "arguments": {
    "query": "quantum computing",
    "limit": 5
  }
}
```

**Example tool call for getting article content:**
```json
{
  "name": "get_article",
  "arguments": {
    "title": "Quantum computing"
  }
}
```

**Example output:**
```
Title: Quantum computing
Summary: Quantum computing is a type of computation that harnesses...
Content: [Full article content with sections, links, and references]
Categories: Computer science, Quantum mechanics, Emerging technologies
Languages: Available in 157 languages
```

---

## Configuration

The server uses environment variables with optional `.env` file support:

- **`MCP_WIKIPEDIA_PORT`** (default: 8006): Server port
- **`MCP_WIKIPEDIA_HOST`** (default: 0.0.0.0): Server host
- **`WIKIPEDIA_USER_AGENT`** (required): User agent string for Wikipedia API requests
- **`WIKIPEDIA_LANGUAGE`** (default: "en"): Wikipedia language edition
- **`LOGGING_LEVEL`** (default: "info"): Logging verbosity level

**Important:** Always set a proper `WIKIPEDIA_USER_AGENT` to identify your application to Wikipedia servers. This is required by Wikipedia's API guidelines.

---

## Example Client Integration

```python
import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI

async def main():
    # Initialize LLM
    model = ChatOpenAI(model="gpt-4")

    # Connect to MCP server
    async with MultiServerMCPClient({
        "wikipedia": {
            "url": "http://localhost:8006/sse",
            "transport": "sse",
        }
    }) as client:
        # Get available tools
        tools = client.get_tools()

        # Create ReAct agent
        agent = create_react_agent(model, tools)

        # Example query
        response = await agent.ainvoke({
            "messages": [{
                "role": "user",
                "content": "Search for information about artificial intelligence and get a summary"
            }]
        })

        print(response["messages"][-1].content)

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Troubleshooting

- **Missing dependencies:** Ensure you have Python 3.12+ and all dependencies installed (`uv sync` or `pip install -e .[dev]`)
- **Wikipedia API errors:** Check your `WIKIPEDIA_USER_AGENT` is properly set and descriptive
- **Docker networking:** If running the server in Docker, use `host.docker.internal` as the host for local clients
- **Language issues:** Verify the `WIKIPEDIA_LANGUAGE` code exists (e.g., "en", "fr", "de", "es")
- **Rate limiting:** Wikipedia may rate limit requests; ensure your user agent is compliant with their guidelines
- **Environment variables:** Double-check your `.env` file format and variable names

---

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Create a Pull Request

---

## License

This project is licensed under the MIT License.
