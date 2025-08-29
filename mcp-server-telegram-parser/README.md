# MCP Telegram Parser Server

> **General:** This repository provides an MCP (Model Context Protocol) server for parsing recent messages from public Telegram channels using Telethon.

## Overview

This service exposes a tool for LLM agents to fetch recent posts from public Telegram channels with structured output. It relies on Telethon and a user session to access public channels without needing a bot.

## MCP Tools:

1. `parse_telegram_channels`
    - **Description:** Retrieves the last N messages from a list of public Telegram channels.
    - **Input:**
        - `channels` (required): A list of channel usernames (e.g., `["durov", "nytimes"]`).
        - `limit` (optional): The number of recent messages to fetch per channel (default: 10).
    - **Output:** A structured result containing the messages from each channel, including text, date, views, and forwards.

## Requirements

- Python 3.12+
- UV (for dependency management)
- Telethon API credentials (API ID and Hash from `my.telegram.org`)
- A Telethon user session (StringSession is recommended)
- Docker (optional, for containerization)

## Setup

1. **Clone the Repository**:
   ```bash
   # path: /path/to/your/projects/
   git clone <repository-url>
   ```

2. **Create `.env` File based on `.env.example`**:
   Create a `.env` file inside `./mcp-server-telegram-parser/`. You must provide your Telethon API credentials and a session string.
   ```dotenv
   # Required Telethon credentials
   TELEGRAM_API_ID="your_api_id"
   TELEGRAM_API_HASH="your_api_hash"
   TELEGRAM_STRING_SESSION="your_string_session"
   ```

3. **Install Dependencies**:
   ```bash
   # path: ./mcp-servers/mcp-server-telegram-parser/
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
docker compose up mcp_server_telegram_parser

# Run the development container with hot-reloading
docker compose -f docker-compose.debug.yml up mcp_server_telegram_parser
```

### Locally

```bash
# path: ./mcp-servers/mcp-server-telegram-parser/
# Basic run
uv run python -m mcp_server_telegram_parser

# Or with custom port and host
uv run python -m mcp_server_telegram_parser --port 8000 --reload
```

### Using Docker (Standalone)

```bash
# path: ./mcp-servers/mcp-server-telegram-parser/
# Build the image
docker build -t mcp-server-telegram-parser .

# Run the container
docker run --rm -it -p 8000:8000 --env-file .env mcp-server-telegram-parser
```

## Testing

At the moment, there are no dedicated tests for this service.

## Project Structure

```
mcp-server-telegram-parser/
├── src/
│   └── mcp_server_telegram_parser/
│       ├── __main__.py
│       ├── logging_config.py
│       ├── schemas.py
│       ├── server.py
│       └── telegram/
│           ├── config.py
│           └── module.py
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

