# Lurky MCP Server

An MCP (Model Context Protocol) server for searching and parsing Twitter Spaces summaries using the Lurky API. This server provides both an MCP interface for AI agents and a standard REST API, with integrated x402 payment support.

## Features

-   **Twitter Spaces Search**: Find discussions and summaries by keyword.
-   **Space Details & Summaries**: Get deep-dive summaries, TL;DRs, and sentiment analysis for specific Twitter Spaces.
-   **Latest Summaries**: Quickly fetch the most recent summaries for any topic.
-   **Smart Caching**: Local PostgreSQL cache to minimize API calls and reduce costs.
-   **Hybrid Interface**: Support for both MCP tools and standard REST endpoints.
-   **Monetization**: Built-in x402 payment protocol support for monetizing tools and endpoints.

## Prerequisites

-   Python 3.12 or higher
-   [uv](https://github.com/astral-sh/uv) (recommended)
-   PostgreSQL database
-   Lurky API Key (get one at [lurky.app](https://lurky.app))

## Installation

1.  Clone the repository:
    ```bash
    git clone <repository-url>
    cd mcp-server-lurky
    ```

2.  Create a `.env` file from the example:
    ```bash
    LURKY_API_KEY=your_lurky_api_key_here
    LURKY_BASE_URL=https://api.lurky.app
    DB_NAME=lurky_db
    DB_USER=postgres
    DB_PASSWORD=postgres
    DB_HOST=localhost
    DB_PORT=5432
    ```

3.  Install dependencies:
    ```bash
    uv sync
    ```

## Usage

### Running the Server

Start the FastAPI/MCP server:

```bash
uv run python -m mcp_server_lurky
```

The server will be available at `http://0.0.0.0:8000`.

### MCP Integration

The MCP server is mounted at `http://0.0.0.0:8000/mcp`. You can use it with any MCP-compatible client.

**Available MCP Tools:**

-   `lurky_search_spaces`: Search for Twitter Spaces discussions based on a keyword.
-   `lurky_get_space_details`: Get full details, summary, and segmented discussions for a specific Space ID.
-   `lurky_get_latest_summaries`: Fetch the latest N unique Twitter Space summaries for a given topic.

### REST API

-   `GET /api/health`: Health check.
-   `GET /hybrid/search?q=keyword`: Search for spaces.
-   `GET /hybrid/spaces/{space_id}`: Get space details.
-   `GET /hybrid/latest-summaries?topic=topic`: Get latest summaries.

## x402 Payment Integration

This server uses the x402 protocol for monetization. Pricing for each tool and endpoint is defined in `tool_pricing.yaml`.

To enable payments, configure the following in your `.env`:
```bash
MCP_LURKY_X402_PRICING_MODE=on
MCP_LURKY_X402_PAYEE_WALLET_ADDRESS=your_wallet_address
MCP_LURKY_X402_CDP_API_KEY_ID=your_cdp_id
MCP_LURKY_X402_CDP_API_KEY_SECRET=your_cdp_secret
```

## Docker

You can run the server using Docker:

```bash
docker build -t mcp-server-lurky .
docker run -p 8000:8000 --env-file .env mcp-server-lurky
```

## License

MIT
