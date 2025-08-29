# MCP Telegram Server

> **General:** This repository provides an MCP (Model Context Protocol) server for posting messages to a Telegram channel.

## Overview

This server provides a tool to send messages to a pre-configured Telegram channel using a bot token. It handles interactions with the Telegram Bot API, including text formatting and message length constraints.

## MCP Tools:

1. `post_to_telegram`
    - **Description:** Posts a given message to the pre-configured Telegram channel.
    - **Input:**
        - `message` (required): The text message content to post.
    - **Output:** A success or failure message.

## Requirements

- Python 3.12+
- UV (for dependency management)
- Telegram Bot Token and Channel ID
- Docker (optional, for containerization)

## Setup

1. **Clone the Repository**:
   ```bash
   # path: /path/to/your/projects/
   git clone <repository-url>
   ```

2. **Create `.env` File based on `.env.example`**:
   Create a `.env` file inside `./mcp-server-telegram/`. You must provide your Telegram bot token and channel ID.
   ```dotenv
   # Required environment variables
   TELEGRAM_TOKEN="your_bot_token_here"
   TELEGRAM_CHANNEL="your_channel_id_or_@username"
   ```

3. **Install Dependencies**:
   ```bash
   # path: ./mcp-servers/mcp-server-telegram/
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
docker compose up mcp_server_telegram

# Run the development container with hot-reloading
docker compose -f docker-compose.debug.yml up mcp_server_telegram
```

### Locally

```bash
# path: ./mcp-servers/mcp-server-telegram/
# Basic run
uv run python -m mcp_server_telegram

# Or with custom port and host
uv run python -m mcp_server_telegram --port 8000 --reload
```

### Using Docker (Standalone)

```bash
# path: ./mcp-servers/mcp-server-telegram/
# Build the image
docker build -t mcp-server-telegram .

# Run the container
docker run --rm -it -p 8000:8000 --env-file .env mcp-server-telegram
```

## Testing

```bash
# path: ./mcp-servers/mcp-server-telegram/
# Run all tests
uv run pytest
```

## Project Structure

```
mcp-server-telegram/
├── src/
│   └── mcp_server_telegram/
│       └── telegram/
│           ├── __init__.py
│           ├── config.py
│           └── module.py
│       ├── __init__.py
│       ├── __main__.py
│       ├── logging_config.py
│       └── server.py
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

