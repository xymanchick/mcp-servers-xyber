# MCP Hangman Server

> **General:** This repository provides an MCP (Model Context Protocol) server for playing a game of Hangman.

## Overview

This server allows users to play Hangman through MCP tools. It manages the game state for each player in memory, allowing for interactive gameplay sessions. A unique `player_id` is used to track the progress of each game.

## MCP Tools:

1. `start_game`
    - **Description:** Starts a new game of Hangman with a given secret word.
    - **Input:**
        - `secret_word` (required): The word to be guessed. Must be alphabetic characters only.
        - `max_attempts` (optional): The number of allowed incorrect guesses (default is 6).
    - **Output:** The initial `GameState`.

2. `guess_letter`
    - **Description:** Makes a guess in an ongoing game.
    - **Input:**
        - `player_id` (required): The ID of the game session, returned by `start_game`.
        - `letter` (required): The single alphabetic character to guess.
    - **Output:** The updated `GameState`.

### GameState Object

Both tools return a `GameState` object with the following structure:
```json
{
  "player_id": "string",
  "masked_word": "list[str]",
  "remaining_attempts": "int",
  "correct_guesses": "list[str]",
  "incorrect_guesses": "list[str]",
  "status": "string" // e.g., 'in_progress', 'won', 'lost'
}
```

## Requirements

- Python 3.12+
- UV (for dependency management)
- Docker (optional, for containerization)

## Setup

1. **Clone the Repository**:
   ```bash
   # path: /path/to/your/projects/
   git clone <repository-url>
   ```

2. **Install Dependencies**:
   ```bash
   # path: ./mcp-servers/mcp-server-hangman/
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
docker compose up mcp_server_hangman

# Run the development container with hot-reloading
docker compose -f docker-compose.debug.yml up mcp_server_hangman
```

### Locally

```bash
# path: ./mcp-servers/mcp-server-hangman/
# Basic run
uv run python -m mcp_server_hangman

# Or with custom port and host
uv run python -m mcp_server_hangman --port 8000 --reload
```

### Using Docker (Standalone)

```bash
# path: ./mcp-servers/mcp-server-hangman/
# Build the image
docker build -t mcp-server-hangman .

# Run the container
docker run --rm -it -p 8000:8000 mcp-server-hangman
```

## Testing

```bash
# path: ./mcp-servers/mcp-server-hangman/
# Run all tests
uv run pytest
```

## Project Structure

```
mcp-server-hangman/
├── src/
│   └── mcp_server_hangman/
│       ├── __init__.py
│       ├── __main__.py              # Entry point (CLI + uvicorn)
│       ├── app.py                   # Application factory & lifespan
│       ├── config.py                # Settings configuration
│       ├── logging_config.py        # Logging configuration
│       ├── dependencies.py          # FastAPI dependency injection
│       ├── schemas.py               # Pydantic request/response models
│       ├── x402_config.py           # x402 payment configuration
│       │
│       ├── api_routers/             # API-Only endpoints (REST)
│       │   ├── __init__.py
│       │   └── health.py            # Health check endpoint
│       ├── hybrid_routers/          # Hybrid endpoints (REST + MCP)
│       │   ├── __init__.py
│       │   ├── pricing.py           # Tool pricing configuration
│       │   ├── start_game.py        # Start new hangman game
│       │   └── guess_letter.py      # Make letter guess
│       ├── middlewares/
│       │   ├── __init__.py
│       │   └── x402_wrapper.py      # x402 payment middleware
│       │
│       └── hangman/                 # Business logic layer
│           ├── models.py            # Game state models
│           └── module.py            # Core game logic
│
├── tests/
├── Dockerfile
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


