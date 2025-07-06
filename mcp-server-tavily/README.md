# MCP Server - Tavily Web Search

> **General:** This repository provides an MCP (Model Context Protocol) server implementation
> for interacting with the Tavily AI web search API.

## Overview

This project implements a microservice that exposes Tavily web search functionality through the Model Context Protocol (MCP). It uses the `langchain-tavily` library to interact with the Tavily Search API.

## MCP Tools:


1. `tavily_web_search`
    - **Description:** Performs a web search using the Tavily API based on the provided query.
    - **Input:**
        - query (str): The search query.
        - max_results (int, optional): Maximum number of results to return.
    - **Output:** A string containing formatted search results, including titles, URLs, and snippets of content. May also include raw JSON data depending on internal formatting.

## Requirements

- Python 3.12+
- UV (for dependency management)
- Docker (optional, for containerization)

## Setup

1.  **Clone the Repository:**
    ```bash
    git clone <repository-url>
    cd mcp-server-tavily
    ```
2.  **Create `.env` File based on `.env.example`**:
    ```dotenv
   # Example environment variables
   TAVILY_API_KEY=YourKey
   TAVILY_MAX_RESULTS=1000
   MCP_TAVILY_HOST="0.0.0.0"
   MCP_TAVILY_PORT=8000
   LOGGING_LEVEL="info"
   ```

3.  **Install Dependencies:**
    ```bash
    uv sync .
    ```

## Running the Server

### Locally

```bash
# Basic run
python -m mcp_server_tavily

# Custom port and host
python -m mcp_server_tavily --host 127.0.0.1 --port 8005
```

### Using Docker

```bash
# Build the image
docker build -t mcp-server-tavily .

# Run the container
docker run --rm -it -p 8005:8005 --env-file .env mcp-server-tavily
```

## Example Client
When server startup is completed, any MCP client
can utilize connection to it

```python
import os
import asyncio
import logging
import sys
import json
from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langchain_together import ChatTogether
from langchain_core.tools import StructuredTool
from langchain_core.messages import HumanMessage

async def main():
    try:
        logger.info("Starting the Tavily MCP client example")

        # --- LLM Setup  ---
        llm_api_key = os.getenv('TOGETHER_API_KEY')
        if not llm_api_key:
             logger.warning("LLM API Key not found. Agent invocation will likely fail.")
             model = None
        else:
            model = ChatTogether(model="meta-llama/Llama-3.3-70B-Instruct-Turbo", api_key=llm_api_key)


        logger.info("Connecting to MCP Tavily server")
        tavily_server_url = f"http://localhost:{os.getenv('MCP_TAVILY_PORT', 8005)}/sse"

        async with MultiServerMCPClient(
            {
                "tavily_web_search": {
                    "url": tavily_server_url,
                    "transport": "sse"
                }
            }
        ) as client:

            logger.info("Fetching available tools from MCP server(s)")
            tools: list[StructuredTool] = client.get_tools()

            if not tools:
                logger.error(f"No tools found from server at {tavily_server_url}. Exiting.")
                return

            logger.info(f"Available tools: {[tool.name for tool in tools]}")
            for tool in tools:
                logger.info(f"Tool Details: Name='{tool.name}', Description='{tool.description}', Args={tool.args_schema}")

            # --- DIRECT RAW TESTING ---
            logger.info("--- DIRECT RAW TESTING ---")
            tavily_tool = next((t for t in tools if t.name == "tavily_web_search"), None)

            if tavily_tool:
                search_query = "What are the latest trends in artificial intelligence?"

                logger.info(f"Searching for: '{search_query}'")
                try:
                    logger.info("1. Testing .ainvoke() method:")
                    raw_result_1 = await tavily_tool.ainvoke({"query": search_query, "max_results": 5})

                    # Print raw results
                    logger.info("RAW RESULT TYPE FROM .ainvoke(): " + str(type(raw_result_1)))
                    logger.info("RAW RESULT FROM .ainvoke():")
                    logger.info(raw_result_1)
                    print("Direct Console Output .ainvoke():")
                    print(raw_result_1)

                    # Extract raw JSON data if present
                    if isinstance(raw_result_1, str) and "ORIGINAL_RAW_DATA:" in raw_result_1:
                        try:
                            raw_json_part = raw_result_1.split("ORIGINAL_RAW_DATA:")[1].split("\n\n")[0]
                            parsed_data = json.loads(raw_json_part)
                            logger.info("SUCCESSFULLY EXTRACTED RAW JSON DATA:")
                            logger.info(f"Query: {parsed_data.get('query', 'N/A')}")
                            logger.info(f"Result count: {len(parsed_data.get('results', []))}")

                            print("=== EXTRACTED SEARCH RESULTS ===")
                            for i, result in enumerate(parsed_data.get('results', []), 1):
                                print(f"{i}. Title: {result.get('title', 'N/A')}")
                                print(f"   URL: {result.get('url', '#')}")
                                print(f"   Content: {result.get('content', 'No content preview.')[:200]}...")
                        except Exception as e:
                            logger.error(f"Error parsing embedded JSON: {e}", exc_info=True)

                        # --- Example 2: Using a ReAct Agent (Optional) ---
                        if model:
                            logger.info("--- Example: Using ReAct Agent ---")
                            try:
                                agent_executor = create_react_agent(model, tools)
                                # Ask a question that might use one or more tools
                                agent_prompt = ("Find the latest news about large language models")
                                logger.info(f"Invoking agent with prompt: "{agent_prompt}"")

                                agent_response = await agent_executor.ainvoke({"messages": [HumanMessage(content=agent_prompt)]})

                                logger.info("Agent finished processing.")
                                final_message = agent_response["messages"][-1]
                                logger.info(f"Agent Final Response Type: {type(final_message).__name__}")
                                logger.info("Agent Final Response Content:")
                                print("" + "="*15 + " Agent Final Response " + "="*15)
                                print(final_message.content)
                                print("="*50 + "")

                            except Exception as agent_err:
                                logger.error(f"Error invoking ReAct agent: {agent_err}", exc_info=True)
                        else:
                            logger.info("--- Skipping ReAct Agent Example (LLM not configured) ---")

                except Exception as e:
                    logger.error(f"Search failed: {e}", exc_info=True)
            else:
                logger.warning("Could not find the tavily_web_search tool for testing.")

    except ConnectionRefusedError:
         logger.error(f"Connection refused. Is the MCP Tavily server running at {tavily_server_url}?")
    except Exception as e:
        logger.error(f"An error occurred in the client: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())
```

## Project Structure

```
mcp-server-tavily/
├── src/
│   └── mcp_server_tavily/
│       └── tavily/           # Contains all the business logic
│           ├── __init__.py   # Exports Tavily client components
│           ├── config.py     # Contains module env settings, custom Error classes
│           └── module.py     # Business module core logic (_TavilyService)
│       ├── __init__.py       # Exports core Tavily components from sub-module
│       ├── __main__.py       # Contains uvicorn server setup logic
│       ├── logging_config.py # Contains shared logging configuration
│       └── server.py         # Contains tool schemas/definitions, sets MCP server up
├── .env.example              # Example environment file
├── .gitignore
├── Dockerfile
├── LICENSE
├── pyproject.toml            # Project metadata and dependencies (using Hatchling)
├── README.md                 # This file
└── uv.lock                   # Dependency lock file (managed by uv)
```

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT
