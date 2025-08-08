# MCP Telegram Parser Server

> General: This repository provides an MCP (Model Context Protocol) server for parsing recent messages from public Telegram channels using Telethon (MTProto user API). It follows the same structure and conventions as other MCP servers in this monorepo.

## Overview

This service exposes a tool for LLM agents to fetch recent posts from public Telegram channels with structured output. It relies on Telethon and a user session (StringSession recommended) to access public channels without adding a bot.

## MCP Tools

1. `parse_telegram_channels`
   - **Description**: Retrieves the last N messages from a list of public Telegram channels
   - **Input**:
     - `channels` (required): list[str] of channel usernames (with or without @)
     - `limit` (optional): int number of recent messages per channel (default: 10)
   - **Output**: `TelegramParseResult` with fields:
     - `fetch_timestamp`: RFC3339 datetime with timezone
     - `channels`: mapping of channel name → `{ channel_name, messages_count, messages, error? }`
       - `messages`: list of `{ id, date, text, views?, forwards? }`

## Requirements

- Python 3.12+
- UV (for dependency management)
- Telethon API credentials (API ID and API Hash from `https://my.telegram.org`)
- A user session (preferably a StringSession)
- Docker (optional)

## Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd mcp-server-telegram-parser
   ```

2. Create `.env` from `.env.example` and fill credentials:
   ```dotenv
   TELEGRAM_API_ID=123456
   TELEGRAM_API_HASH="your_api_hash_here"
   # Preferred: StringSession for non-interactive runs
   TELEGRAM_STRING_SESSION="your_single_line_string_session"
   # Optional: file session name if not using StringSession
   TELEGRAM_SESSION_NAME=.telegram_session

   MCP_TELEGRAM_PARSER_HOST=0.0.0.0
   MCP_TELEGRAM_PARSER_PORT=8012
   ```

3. Install dependencies:
   ```bash
   uv sync
   # Or install with dev tools
   uv sync --group dev
   ```

## Running the Server

### Locally

```bash
uv run python -m mcp_server_telegram_parser --host 0.0.0.0 --port 8012
```

### Using Docker

```bash
# Build the image
docker build -t mcp-server-telegram-parser .

# Run the container
docker run --rm -it \
  -p 8012:8012 \
  --env-file .env \
  mcp-server-telegram-parser
```

## Testing

At the moment there are no dedicated tests for this service.

## Example Client

When server startup is completed, any MCP client can utilize connection to it.

The snippet below demonstrates invoking the tool via a generic MCP client approach (adjust to your client stack):

```python
import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI

async def main():
    model = ChatOpenAI(model="gpt-4o-mini")

    client = MultiServerMCPClient({
        "telegram-parser": {
            "url": "http://localhost:8012",
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
            "content": "Parse last 5 messages from nytimes and durov"
        }]
    })

    print(response["messages"][-1].content)

if __name__ == "__main__":
    asyncio.run(main())
```

## Project Structure

```
mcp-server-telegram-parser/
├── src/
│   └── mcp_server_telegram_parser/
│       ├── __main__.py              # Uvicorn server setup
│       ├── logging_config.py        # Logging configuration
│       ├── schemas.py               # Pydantic models for structured output
│       ├── server.py                # MCP tool definitions and app wiring
│       └── telegram/
│           ├── config.py            # ParserConfig (env-driven)
│           └── module.py            # Telethon logic and service
├── .env.example
├── Dockerfile
├── LICENSE
├── pyproject.toml
└── README.md
```

## Authorization Notes

- Use a **StringSession** for non-interactive deployments. Generate once with Telethon and set `TELEGRAM_STRING_SESSION` in `.env`.
- Alternatively, use file sessions by setting `TELEGRAM_SESSION_NAME` and completing the first-run login.
- Treat sessions as secrets. Do not commit them.

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT

