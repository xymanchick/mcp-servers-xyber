# AAVE MCP Server

A Model Context Protocol (MCP) server that provides real-time Aave v3 market data via a clean, agent-friendly schema.

## Overview

This service queries Aave v3 GraphQL across multiple networks and returns a simplified structure:
- Networks (markets) with an aggregated overview
- Per-reserve summaries (APY, totals)
- Optional filtering by network and/or asset

Designed for LLM agents: minimal fields, consistent formatting, and ready-to-use metrics.

## MCP Tools

### `get_available_networks`
- Description: Returns the list of supported networks as known by the upstream API.
- Input: none
- Output: `list[str]`

### `get_comprehensive_aave_data`
- Description: Returns a simplified, comprehensive view of Aave data.
- Inputs:
  - `network` (optional, `str`): restrict results to a single network (e.g., "ethereum", "polygon").
  - `asset_address` (optional, `str`): restrict results to a single token address on the specified network; if `network` is omitted, the server will filter across all networks but still return only matching reserves.
- Output: `ComprehensiveAaveData` with the following shape:
  - `data: list[NetworkAaveData]`
    - `network: str`
    - `overview: MarketOverview`
      - `total_reserves: int`
      - `total_liquidity_usd: str`
      - `total_variable_debt_usd: str`
      - `utilization_rate: str`
      - `base_currency_info: {symbol: str, decimals: int}`
    - `reserves: list[AssetSummary]`
      - `address: str`
      - `symbol: str`
      - `name: str`
      - `supply_apy: str`
      - `borrow_apy: str`
      - `total_supply: str`
      - `total_debt: str`

Notes:
- If both `network` and `asset_address` are provided, only the selected reserve for that network is returned.
- Raw pool data and separate risk blocks are intentionally omitted to reduce duplication and confusion.

## Installation

### Prerequisites
- Python 3.12+
- UV (dependency management)

### Setup

1. Clone the repository
```bash
git clone <repository-url>
cd mcp-server-aave
```

2. Install dependencies
```bash
uv sync
```

3. Configure environment
```bash
cp env.example .env
# Edit .env to suit your environment
```

4. Run the server
```bash
uv run python -m mcp_server_aave
```

## Configuration

Environment variables (see `env.example`):
```dotenv
AAVE_API_BASE_URL=https://api.v3.aave.com/graphql
AAVE_TIMEOUT_SECONDS=30
AAVE_MAX_RETRIES=3
AAVE_ENABLE_CACHING=true
AAVE_CACHE_TTL_SECONDS=300
MCP_AAVE_HOST=0.0.0.0
MCP_AAVE_PORT=8000
LOGGING_LEVEL=INFO
```

## Usage Examples

### Get networks
```python
networks = await get_available_networks()
# ["Ethereum", "Polygon", ...]
```

### Get all markets
```python
data = await get_comprehensive_aave_data()
# data.data[0].overview.total_reserves
# data.data[0].reserves[0].symbol
```

### Filter by network
```python
eth = await get_comprehensive_aave_data(network="ethereum")
# Returns single network entry with its reserves
```

### Filter by network and asset
```python
usdc_eth = await get_comprehensive_aave_data(
    network="ethereum",
    asset_address="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
)
# Returns one network with a single USDC reserve summary
```

## Data Model Notes
- Values are strings to avoid floating point ambiguity and because many LLM clients prefer strings for numeric data.
- APYs are variable-rate and can change; do not treat as guarantees.

## Development

### Tests
```bash
uv run pytest
```

### Lint/format
```bash
uv run ruff check .
uv run black .
uv run isort .
```

### Docker
```bash
docker build -t mcp-server-aave .
docker run -p 8000:8000 mcp-server-aave
```

## License

MIT
