# MCP Deep Researcher Server

## Overview

This MCP server provides an agent-based deep research capability using LangGraph. It integrates with other MCP services like Tavily for web search and Arxiv for academic papers to perform comprehensive research on given topics.

## MCP Tools

1. `deep_research`
   - **Description:** Performs in-depth research on a given topic and generates a structured report.
   - **Input:**
     - research_topic: str (The topic to research)
     - max_web_research_loops: int = 3 (Maximum number of web research iterations)
   - **Output:** JSON string containing the research report with sections like summary, key findings, etc.

## Requirements

- Python 3.12+
- UV (for dependency management) - Install with: `curl -LsSf https://astral.sh/uv/install.sh | sh` or `pip install uv`
- API keys for integrated services (Tavily, Arxiv, APIFY, LLM providers)


## Docker Compose Setup

This guide explains how to run the Deep Researcher MCP server alongside other MCP servers using Docker Compose, with proper inter-service communication.

### Prerequisites

- Docker and Docker Compose installed
- API keys for the services you want to use (Google AI, Together AI, Mistral AI, Tavily, Apify)

### Step-by-Step Setup

#### 1. Add Deep Researcher to docker-compose.yml

Add this service definition to your main `docker-compose.yml` file:

```yaml
  mcp_server_deepresearcher:
    build:
      context: ./mcp-server-deepresearcher
      dockerfile: Dockerfile
    container_name: mcp_server_deepresearcher
    ports:
      - "8011:8000"
    env_file:
      - ./mcp-server-deepresearcher/.env
    command: [
      "python", "-m", "mcp_server_deepresearcher", "--port", "8000"
    ]
    restart: unless-stopped
```

**Important Notes:**
- Do NOT add `network_mode: bridge` - this will break inter-service communication
- The service will automatically join the default Docker Compose network
- Use a unique external port (8011 in this example)

#### 2. Create the Environment File

Create `mcp-server-deepresearcher/.env` with the following content:

```env
# LLM Configuration
TOGETHER_API_KEY=your_together_api_key_here
GOOGLE_API_KEY=your_google_api_key_here
MISTRAL_API_KEY=your_mistral_api_key_here
MODEL_PROVIDER=google
MODEL_NAME=gemini-2.5-flash
MODEL_PROVIDER_SPARE=together
MODEL_NAME_SPARE=deepseek-ai/DeepSeek-V2

# MCP Service URLs - CRITICAL: Use the correct paths!
MCP_TAVILY_URL=http://mcp_server_tavily:8000/mcp-server/mcp
MCP_ARXIV_URL=http://mcp_server_arxiv:8000/mcp-server/mcp

# Optional: Apify for Twitter/social media scraping
APIFY_TOKEN=your_apify_token_here
```

#### 3. Understanding MCP Service URLs

The URL format for MCP services follows this pattern:
```
http://[service_name]:[port]/[mount_path]/[mcp_path]
```

For FastMCP-based services (like tavily and arxiv):
- **Service name**: The container name from docker-compose (e.g., `mcp_server_tavily`)
- **Port**: Internal container port (usually 8000)
- **Mount path**: Where the MCP app is mounted (usually `/mcp-server`)
- **MCP path**: The internal MCP endpoint (usually `/mcp`)

**Complete URL**: `http://mcp_server_tavily:8000/mcp-server/mcp`

#### 4. Build and Start Services

```bash
# Build and start all services
docker-compose up --build -d

# Check that all services are running
docker-compose ps

# View logs for deep researcher
docker-compose logs -f mcp_server_deepresearcher
```

#### 5. Verify Successful Startup

Look for these log messages in the Deep Researcher logs:

```
✅ SUCCESS INDICATORS:
- "LLMs initialized successfully"
- "Tavily MCP server configured" 
- "Arxiv MCP server configured"
- "Successfully fetched X tools for the agent to use"
- "Deep Researcher agent initialized successfully"

❌ ERROR INDICATORS:
- "404 Not Found" - Wrong URL path
- "Name or service not known" - Network configuration issue
- "Connection refused" - Target service not running
- "Session terminated" - MCP protocol issue
```

### Troubleshooting

#### Common Issues and Solutions

##### 1. "404 Not Found" Error
**Problem**: Wrong URL path in `.env` file
**Solution**: Verify the exact path by checking the target service's `__main__.py` file

##### 2. "Name or service not known"
**Problem**: Network configuration issue
**Solution**: 
- Remove any `network_mode: bridge` from the service definition
- Ensure all services are in the same docker-compose file or network

##### 3. "Connection refused"
**Problem**: Target service not running
**Solution**: Check that dependent services (tavily, arxiv) are running:
```bash
docker-compose ps
docker-compose logs mcp_server_tavily
docker-compose logs mcp_server_arxiv
```

##### 4. Service crashes on startup
**Problem**: Missing or invalid API keys
**Solution**: Verify all required API keys are set in the `.env` file

#### Finding MCP Paths for Other Services

To find the correct path for any MCP service:

1. Look at the service's `__main__.py` file
2. Find the `http_app()` call - note the `path` parameter
3. Find the `app.mount()` call - note the mount path
4. Combine them: `[mount_path][mcp_path]`

Example from tavily service:
```python
# In mcp-server-tavily/src/mcp_server_tavily/__main__.py
mcp_app = mcp_server.http_app(path="/mcp", transport="streamable-http")
app.mount("/mcp-server", mcp_app)
# Result: /mcp-server/mcp
```

## Project Structure

```
mcp-server-deepresearcher/
├── src/
│   └── mcp_server_deepresearcher/
│       ├── deepresearcher/
│       │   ├── __init__.py
│       │   ├── config.py
│       │   ├── graph.py
│       │   ├── module.py
│       │   ├── prompts.py
│       │   ├── state.py
│       │   └── utils.py
│       ├── __init__.py
│       ├── __main__.py
│       ├── logging_config.py
│       └── server.py
├── .gitignore
├── Dockerfile
├── LICENSE
├── pyproject.toml
├── README.md
└── uv.lock
```

## Setup (Local Development)

If you prefer to run the server locally instead of using Docker:

1. **Clone the Repository**:
   ```bash
   git clone <repository-url>
   cd mcp-server-deepresearcher
   ```

2. **Create `.env` File**:
   Create a `.env` file in the root directory with the following variables:
   ```env
   # LLM Configuration
   TOGETHER_API_KEY=your_together_api_key
   GOOGLE_API_KEY=your_google_api_key
   MISTRAL_API_KEY=your_mistral_api_key
   MODEL_PROVIDER=google
   MODEL_NAME=gemini-2.5-pro
   MODEL_PROVIDER_SPARE=together
   MODEL_NAME_SPARE=deepseek-ai/DeepSeek-V2

   # MCP URLs for local development
   MCP_TAVILY_URL=http://localhost:8005/mcp-server/mcp
   MCP_ARXIV_URL=http://localhost:8006/mcp-server/mcp
   APIFY_TOKEN=your_apify_token
   ```

3. **Install Dependencies**:
   ```bash
   uv sync
   ```

4. **Run the Server**:
   ```bash
   uv run python -m mcp_server_deepresearcher
   ```

## Graph Visualization

![Deep Researcher Graph](./deep_researcher_graph.png)

This graph illustrates the workflow of the research process, including query generation, web research, summarization, reflection, and finalization.

## License

MIT
