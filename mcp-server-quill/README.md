# Quill MCP Server

An MCP (Model Context Protocol) server for Quill Shield AI security audits. This server provides both an MCP interface for AI agents and a standard REST API to search for tokens and analyze their security on EVM and Solana chains, with integrated x402 payment support.

## Features

- **Token Search**: Find token addresses by name or symbol across multiple chains (Ethereum, BSC, Solana, etc.) using DexScreener.
- **EVM Security**: Analyze security of tokens on EVM-compatible chains using QuillCheck.
- **Solana Security**: Analyze security of tokens on Solana using QuillCheck.
- **Hybrid Interface**: Support for both MCP tools and standard REST endpoints.
- **Monetization**: Built-in x402 payment protocol support for monetizing tools and endpoints.

## Prerequisites

- Python 3.12 or higher
- [uv](https://github.com/astral-sh/uv) (recommended)
- Quill API Key (get one from Quill Audits)

## Installation

1.  Clone the repository (if you haven't already):
    ```bash
    git clone <repository-url>
    cd mcp-server-quill
    ```

2.  Create a `.env` file from the example:
    ```bash
    cp .example.env .env
    ```

3.  Edit `.env` and add your configuration:
    ```bash
    # Required
    QUILL_API_KEY=your_quill_api_key_here
    
    # Optional Server Config
    MCP_QUILL_HOST=0.0.0.0
    MCP_QUILL_PORT=8001
    MCP_QUILL_LOGGING_LEVEL=INFO
    
    # Optional Payment Config (x402)
    MCP_QUILL_X402_PRICING_MODE=off  # Set to 'on' to enable payments
    MCP_QUILL_X402_PAYEE_WALLET_ADDRESS=your_wallet_address
    MCP_QUILL_X402_CDP_API_KEY_ID=your_cdp_id
    MCP_QUILL_X402_CDP_API_KEY_SECRET=your_cdp_secret
    ```

4.  Install dependencies:
    ```bash
    uv sync
    ```

## Usage

### MCP Integration

The MCP server is mounted at `http://localhost:8001/mcp`. You can use it with any MCP-compatible client (like Cursor, Claude Desktop, etc.).

**Available MCP Tools:**

-   `search_token_address`: Search for a token's contract address by name or symbol across chains.
-   `get_evm_token_info`: Get comprehensive security analysis for an EVM-compatible token (Ethereum, BSC, Polygon, etc.).
-   `get_solana_token_info`: Get comprehensive security analysis for a Solana token.

### REST API

The server exposes standard REST endpoints for direct integration:

-   `GET /api/health`: Health check.
-   `GET /search/{query}?chain={chain}`: Search for a token address.
-   `GET /evm/{query}?quill_chain_id={id}`: Get EVM token security analysis.
-   `GET /solana/{query}`: Get Solana token security analysis.

Documentation is available at `http://localhost:8001/docs`.

## x402 Payment Integration

This server uses the x402 protocol for monetization. Pricing for each tool and endpoint is defined in `tool_pricing.yaml`.

To enable payments, set `MCP_QUILL_X402_PRICING_MODE=on` in your `.env` and configure your wallet and CDP credentials.

## Running the Server

You can run the server in two ways:

### Option 1: Docker (Recommended for Production)

The easiest way to run the server in Docker is using the provided script:

```bash
# Make sure scripts are executable
chmod +x scripts/*.sh

# Start the server in Docker (will build image if needed)
./scripts/start-docker.sh

# Rebuild and restart
./scripts/start-docker.sh --rebuild

# Restart on a different port
./scripts/start-docker.sh --restart --port 8002
```

The script will:
- Check if Docker is running
- Build the Docker image if it doesn't exist
- Start the server container with proper configuration
- Map port 8001 (or custom port) to the container
- Show logs automatically

**Available options:**
- `--restart`: Stop and restart the container
- `--rebuild`: Rebuild the Docker image and restart
- `--port PORT`: Specify a custom port (default: 8001)
- `--help`: Show help message

### Option 2: Local Development

The easiest way to start the server locally is using the provided script:

```bash
# Start the server
./scripts/start-server.sh
```

The script will:
- Check for `uv` installation
- Create `.env` from example if missing
- Start the server on `http://localhost:8001` using Python 3.12

### Manual Start

You can also run the server manually using `uv`:

```bash
uv run --python 3.12 python -m mcp_server_quill
```

## Testing

Run tests using pytest:

```bash
# Install test dependencies
uv sync --group dev

# Run all tests
uv run pytest

# Run specific test files
uv run pytest tests/hybrid_routers/test_security.py

# Run with verbose output
uv run pytest -v
```

## License

MIT
