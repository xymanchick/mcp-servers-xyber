# mcp-server-quill

A Model Context Protocol (MCP) server for Quill Shield AI security audits. This server provides both REST API endpoints and MCP tools to search for tokens and analyze their security on EVM and Solana chains.

## Features

- **Token Search**: Find token addresses by name or symbol across multiple chains (Ethereum, BSC, Solana, etc.) using DexScreener.
- **EVM Security**: Analyze security of tokens on EVM-compatible chains using QuillCheck.
- **Solana Security**: Analyze security of tokens on Solana using QuillCheck.
- **Hybrid Support**: Exposes functionality as both standard REST API endpoints and MCP tools for AI agents.

## Configuration

The server can be configured via environment variables or a `.env` file.

| Variable | Description | Default |
|----------|-------------|---------|
| `MCP_QUILL_HOST` | Host to bind the server to | `0.0.0.0` |
| `MCP_QUILL_PORT` | Port to listen on | `8000` |
| `MCP_QUILL_LOGGING_LEVEL` | Logging level | `INFO` |
| `QUILL_API_KEY` | API Key for QuillCheck | **Required** |
| `QUILL_BASE_URL` | Base URL for QuillCheck API | `https://check-api.quillai.network/api/v1` |

## Installation

### Using uv (Recommended)

```bash
# Install dependencies
uv sync

# Run the server
uv run python -m mcp_server_quill
```

### Using Docker

```bash
docker build -t mcp-server-quill .
docker run -p 8000:8000 --env-file .env mcp-server-quill
```

## API Endpoints

### REST API

- `GET /hybrid/search/{query}`: Search for a token address.
- `GET /hybrid/evm/{query}`: Get EVM token security analysis.
- `GET /hybrid/solana/{query}`: Get Solana token security analysis.
- `GET /api/health`: Health check.

### MCP Tools

The server exposes the following tools to MCP clients:

- `search_token_address`: Search for a token's contract address.
- `get_evm_token_info`: Get comprehensive security analysis for an EVM-compatible token.
- `get_solana_token_info`: Get comprehensive security analysis for a Solana token.

## Development

```bash
# Run in development mode with hot reload
uv run python -m mcp_server_quill --reload
```
