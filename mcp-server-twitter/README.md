# MCP Twitter Server

> **General:** This repository provides an MCP (Model Context Protocol) server for performing actions on Twitter (now X).
> It demonstrates a **hybrid architecture** that exposes functionality through REST APIs, MCP, or both simultaneously.

## Capabilities

### 1. **API-Only Endpoints** (`/api`)

Standard REST endpoints for traditional clients (e.g., web apps, dashboards).

| Method | Endpoint              | Price      | Description                            |
| :----- | :-------------------- | :--------- | :------------------------------------- |
| `GET`  | `/api/health`         | **Free**   | Checks the server's operational status |

### 2. **Hybrid Endpoints** (`/hybrid`)

Accessible via both REST and as MCP tools. Ideal for functionality shared between humans and AI.

| Method/Tool                 | Price      | Description                         |
| :-------------------------- | :--------- | :---------------------------------- |
| `GET /hybrid/pricing`       | **Free**   | Returns tool pricing configuration  |

### 3. **MCP-Only Endpoints**

Tools exposed exclusively to AI agents. Not available as REST endpoints.

| Tool                    | Price      | Description                                   |
| :---------------------- | :--------- | :-------------------------------------------- |
| `create_tweet`          | **Paid**   | Creates a new tweet with optional media       |
| `get_user_tweets`       | **Paid**   | Retrieves recent tweets from a list of users  |
| `follow_user`           | **Paid**   | Follows a user                                |
| `retweet_tweet`         | **Paid**   | Retweets a tweet                              |
| `get_trends`            | **Paid**   | Retrieves trending topics for countries       |
| `search_hashtag`        | **Paid**   | Searches for recent tweets with a hashtag     |

#### Tool Details:

1.  `create_tweet`
    - **Input:** `text` (required), `image_content` (optional), `poll_options` (optional), `poll_duration` (optional), `in_reply_to_tweet_id` (optional), `quote_tweet_id` (optional).
    - **Output:** The ID of the created tweet.

2.  `get_user_tweets`
    - **Input:** `user_ids` (required, list), `max_results` (optional).
    - **Output:** A dictionary mapping user IDs to their recent tweet texts.

3.  `follow_user`
    - **Input:** `user_id` (required).
    - **Output:** A success message.

4.  `retweet_tweet`
    - **Input:** `tweet_id` (required).
    - **Output:** A success message.

5.  `get_trends`
    - **Input:** `countries` (required, list), `max_trends` (optional).
    - **Output:** A dictionary mapping countries to their trending topics.

6.  `search_hashtag`
    - **Input:** `hashtag` (required), `max_results` (optional).
    - **Output:** A list of tweet texts matching the hashtag.

*Note: Paid endpoints require x402 payment protocol configuration. See `.env.example` for details.*

## API Documentation

This server automatically generates OpenAPI documentation. Once the server is running, you can access the interactive API docs at:

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs) (for REST endpoints)
- **MCP Inspector**: Use an MCP-compatible client to view available agent tools [http://localhost:8000/mcp](http://localhost:8000/mcp)

These interfaces allow you to explore all REST-accessible endpoints, view their schemas, and test them directly from your browser.

## Requirements

- **Python 3.12+**
- **UV** (for dependency management)
- **Twitter Developer API credentials** (API key, secret, access tokens, bearer token)
- **Docker** (optional, for containerization)

## Setup

1.  **Clone & Configure**
    ```bash
    git clone <repository-url>
    cd mcp-server-twitter
    cp .env.example .env
    # Configure environment for Twitter API credentials, x402, logging, etc. (see .env.example).
    ```

2.  **Virtual Environment**
    ```bash
    # working directory: ./mcp-servers/mcp-server-twitter/
    uv sync
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

# Run with verbose output
uv run pytest -v
```

## Project Structure

```
mcp-server-twitter/
├── src/
│   └── mcp_server_twitter/
│       ├── __init__.py
│       ├── __main__.py              # Entry point (CLI + uvicorn)
│       ├── app.py                   # Application factory & lifespan
│       ├── errors.py                # Custom error definitions
│       ├── logging_config.py        # Logging configuration
│       ├── metrics.py               # Prometheus metrics
│       ├── schemas.py               # Pydantic request/response models
│       ├── x402_config.py           # x402 payment configuration
│       │
│       ├── api_routers/             # API-Only endpoints (REST)
│       │   ├── __init__.py
│       │   └── health.py            # Health check endpoint
│       │
│       ├── hybrid_routers/          # Hybrid endpoints (REST + MCP)
│       │   ├── __init__.py
│       │   └── pricing.py           # Pricing information endpoint
│       │
│       ├── mcp_routers/             # MCP-Only endpoints
│       │   ├── __init__.py
│       │   ├── create_tweet.py      # Create tweets
│       │   ├── follow_user.py       # Follow Twitter users
│       │   ├── get_trends.py        # Get trending topics
│       │   ├── get_user_tweets.py   # Fetch user tweets
│       │   ├── retweet_tweet.py     # Retweet functionality
│       │   └── search_hashtag.py    # Search by hashtag
│       │
│       ├── middlewares/
│       │   ├── __init__.py
│       │   └── x402_wrapper.py      # x402 payment middleware
│       │
│       └── twitter/                 # Business logic layer
│           ├── __init__.py
│           ├── config.py
│           ├── models.py
│           └── module.py            # Twitter API integration
│
├── tests/
├── .env.example
├── Dockerfile
├── pyproject.toml
└── README.md
```

## Twitter API Configuration

This server requires Twitter Developer API credentials to interact with the Twitter platform. All credentials must be configured via environment variables.

### Required Environment Variables

Set the following environment variables in your `.env` file:

```bash
# Required Twitter API credentials
TWITTER_API_KEY="your_api_key"
TWITTER_API_SECRET_KEY="your_api_secret_key"
TWITTER_ACCESS_TOKEN="your_access_token"
TWITTER_ACCESS_TOKEN_SECRET="your_access_token_secret"
TWITTER_BEARER_TOKEN="your_bearer_token"
```

### Obtaining Twitter API Credentials

1. Apply for a Twitter Developer Account at [developer.twitter.com](https://developer.twitter.com)
2. Create a new App in the Twitter Developer Portal
3. Generate your API keys and access tokens
4. Add the credentials to your `.env` file

### Error Handling

- If the required credentials are not configured, the server will fail to start with an error message indicating which credentials are missing.
- If the Twitter API rejects the credentials (for example, invalid or revoked tokens), the server will respond with appropriate error messages for each failed request.

## Contributing

1.  Fork the repository
2.  Create your feature branch
3.  Commit your changes
4.  Push to the branch
5.  Create a Pull Request

## License

MIT