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
- UV (for dependency management)
- API keys for integrated services (Tavily, Arxiv, APIFY, LLM providers)

## Setup

1. **Clone the Repository**:
   ```bash
   git clone <repository-url>
   cd mcp-server-deepresearcher
   ```

2. **Create `.env` File**:
   Create a `.env` file in the root directory with the following variables (adjust based on your configuration):
   ```
   # LLM Configuration
   LLM_PROVIDER=google
   LLM_MODEL=gemini-2.5-flash
   LLM_API_KEY=your_keys


   # Spare LLM Configuration (optional)
   SPARE_LLM_PROVIDER=together
   SPARE_LLM_MODEL=deepseekV3
   SPARE_LLM_API_KEY=your_api_key


   # Search MCP Configuration
   APIFY_TOKEN=your_apify_token
   MCP_TAVILY_URL=http://localhost:8001
   MCP_ARXIV_URL=http://localhost:8002
   other mcp servers
   ```

3. **Install Dependencies**:
   ```bash
   uv sync
   ```

## Running the Server

### Locally
```bash
uv run python -m mcp_server_deepresearcher
```

### Using Docker
```bash
docker build -t mcp-server-deepresearcher .
docker run -p 8000:8000 --env-file .env mcp-server-deepresearcher
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

## License

MIT


# Deep Researcher

## Description

Deep Researcher is an AI-powered research agent built with LangGraph. It uses large language models (LLMs) and multi-server MCP tools to perform in-depth web research on given topics, generating structured summaries and reports.

## Graph Visualization

![Deep Researcher Graph](./src/deep_researcher_graph.png)

This graph illustrates the workflow of the research process, including query generation, web research, summarization, reflection, and finalization.

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-repo/deep-researcher.git
   cd deep-researcher
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables (e.g., API keys for MCP servers) in a `.env` file.

## Usage

Run the main script with a research topic:

```bash
python src/main.py
```

The script will output the research results and save them to `final_research.json` and `final_research.py`.

You can customize the research topic in `src/main.py`.

## Features
- Parallel web research using multiple MCP servers
- Iterative summarization and reflection for deeper insights
- Structured JSON output with title, executive summary, key findings, and sources

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.
