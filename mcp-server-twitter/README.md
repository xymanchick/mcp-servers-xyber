# MCP Twitter Server

> **General:** This repository provides an MCP (Model Context Protocol) server for performing actions on Twitter (now X).

## Overview

This server exposes a comprehensive set of tools for interacting with the Twitter API. It allows language models and AI agents to create tweets, fetch user information, follow users, retweet, and search for trends and hashtags.

## MCP Tools:

1.  `create_tweet`
    - **Description:** Creates a new tweet.
    - **Input:** `text` (required), `image_content` (optional), `poll_options` (optional), `poll_duration` (optional), `in_reply_to_tweet_id` (optional), `quote_tweet_id` (optional).
    - **Output:** The ID of the created tweet.

2.  `get_user_tweets`
    - **Description:** Retrieves recent tweets from a list of users.
    - **Input:** `user_ids` (required, list), `max_results` (optional).
    - **Output:** A dictionary mapping user IDs to their recent tweet texts.

3.  `follow_user`
    - **Description:** Follows a user.
    - **Input:** `user_id` (required).
    - **Output:** A success message.

4.  `retweet_tweet`
    - **Description:** Retweets a tweet.
    - **Input:** `tweet_id` (required).
    - **Output:** A success message.

5.  `get_trends`
    - **Description:** Retrieves trending topics for one or more countries.
    - **Input:** `countries` (required, list), `max_trends` (optional).
    - **Output:** A dictionary mapping countries to their trending topics.

6.  `search_hashtag`
    - **Description:** Searches for recent tweets with a specific hashtag.
    - **Input:** `hashtag` (required), `max_results` (optional).
    - **Output:** A list of tweet texts matching the hashtag.

## Requirements

- Python 3.12+
- UV (for dependency management)
- Twitter Developer API credentials
- Docker (optional, for containerization)

## Setup

1.  **Clone the Repository**:
    ```bash
    # path: /path/to/your/projects/
    git clone <repository-url>
    ```

2.  **Create `.env` File based on `.env.example`**:
    Create a `.env` file inside `./mcp-server-twitter/`. You must provide your Twitter API credentials.
    ```dotenv
    # Required Twitter API credentials
    TWITTER_API_KEY="your_api_key"
    TWITTER_API_SECRET_KEY="your_api_secret_key"
    TWITTER_ACCESS_TOKEN="your_access_token"
    TWITTER_ACCESS_TOKEN_SECRET="your_access_token_secret"
    TWITTER_BEARER_TOKEN="your_bearer_token"
    ```

3.  **Install Dependencies**:
    ```bash
    # path: ./mcp-servers/mcp-server-twitter/
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
docker compose up mcp_server_twitter

# Run the development container with hot-reloading
docker compose -f docker-compose.debug.yml up mcp_server_twitter
```

### Locally

```bash
# path: ./mcp-servers/mcp-server-twitter/
# Basic run
uv run python -m mcp_server_twitter

# Or with custom port and host
uv run python -m mcp_server_twitter --port 8000 --reload
```

### Using Docker (Standalone)

```bash
# path: ./mcp-servers/mcp-server-twitter/
# Build the image
docker build -t mcp-server-twitter .

# Run the container
docker run --rm -it -p 8000:8000 --env-file .env mcp-server-twitter
```

## Testing

```bash
# path: ./mcp-servers/mcp-server-twitter/
# Run all tests
uv run pytest
```

## Project Structure

```
mcp-server-twitter/
├── src/
│   └── mcp_server_twitter/
│       ├── twitter/
│       │   ├── __init__.py
│       │   ├── config.py
│       │   └── module.py
│       ├── __init__.py
│       ├── __main__.py
│       ├── errors.py
│       ├── logging_config.py
│       ├── metrics.py
│       ├── server.py
│       └── schemas.py
├── tests/
│   ├── test_module.py
│   └── test_server.py
├── .env.example
├── .gitignore
├── Dockerfile
├── LICENSE
├── pyproject.toml
├── README.md
└── uv.lock
```

## Contributing

1.  Fork the repository
2.  Create your feature branch
3.  Commit your changes
4.  Push to the branch
5.  Create a Pull Request

## License

MIT