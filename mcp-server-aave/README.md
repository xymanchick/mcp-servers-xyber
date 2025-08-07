# AAVE MCP Server

A Model Context Protocol (MCP) server that provides comprehensive AAVE DeFi protocol data for financial analysis and investment decision-making.

## Overview

This MCP server integrates with the AAVE DeFi protocol to provide real-time data on:

- **Pool Data**: Comprehensive information about AAVE pools across multiple networks
- **Reserve Data**: Detailed APY rates, liquidity, and risk parameters for specific assets
- **Risk Assessment**: Asset-specific risk metrics and market analysis for investment decisions
- **Comprehensive Analysis**: All data in one structured response for efficient agent processing

## Features

### 🔗 Multi-Network Support
- Ethereum Mainnet
- Polygon
- Avalanche
- Arbitrum
- Optimism

### 📊 Financial Data
- Real-time APY rates (supply and borrow)
- Liquidity utilization metrics
- Risk parameters (LTV, liquidation thresholds)
- Market capitalization and volume data

### 🛡️ Risk Assessment
- Asset volatility analysis
- Correlation with ETH
- Liquidity scoring
- Concentration risk metrics
- Protocol-specific risk factors

### ⚡ Performance
- Intelligent caching with configurable TTL
- Retry logic with exponential backoff
- Async/await architecture for high concurrency
- Comprehensive error handling

## Installation

### Prerequisites
- Python 3.12+
- uv package manager

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd mcp-server-aave
   ```

2. **Install dependencies**
   ```bash
   uv sync
   ```

3. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Run the server**
   ```bash
   uv run python -m mcp_server_weather
   ```

## Configuration

### Environment Variables

```bash
# Blockchain Configuration
AAVE_RPC_URL=https://eth-mainnet.g.alchemy.com/v2/your-api-key
AAVE_NETWORK=ethereum

# API Configuration
AAVE_API_BASE_URL=https://aave-api-v2.aave.com
AAVE_TIMEOUT_SECONDS=30
AAVE_MAX_RETRIES=3

# Caching
AAVE_ENABLE_CACHING=true
AAVE_CACHE_TTL_SECONDS=300

# Risk Parameters
AAVE_MAX_SLIPPAGE_PERCENT=0.5
AAVE_MIN_HEALTH_FACTOR=1.1
```

### Supported Networks

| Network | Chain ID | Status |
|---------|----------|--------|
| Ethereum | 1 | ✅ Active |
| Polygon | 137 | ✅ Active |
| Avalanche | 43114 | ✅ Active |
| Arbitrum | 42161 | ✅ Active |
| Optimism | 10 | ✅ Active |

## API Endpoints

### MCP Tools

The server exposes both individual tools and a comprehensive tool for financial analysis:

#### Individual Tools

##### `get_pool_data`
Get comprehensive AAVE pool data for a specific network.

**Parameters:**
- `network` (optional): Blockchain network (default: "ethereum")

**Returns:** Pool data including reserves, APY, and market information

##### `get_reserve_data`
Get detailed reserve data for a specific asset.

**Parameters:**
- `asset_address`: Token contract address
- `network` (optional): Blockchain network (default: "ethereum")

**Returns:** Reserve data including APY, liquidity, and risk parameters

##### `get_asset_risk_data`
Get risk assessment data for a specific asset.

**Parameters:**
- `asset_address`: Token contract address
- `network` (optional): Blockchain network (default: "ethereum")

**Returns:** Risk metrics including volatility, correlation, and risk scores

#### Comprehensive Tool

##### `get_comprehensive_aave_data`
Get comprehensive AAVE DeFi protocol data for financial analysis and investment decisions.

**Parameters:**
- `network` (optional): Blockchain network (default: "ethereum")
- `asset_address` (optional): Specific token contract address for detailed analysis

**Returns:** ComprehensiveAaveData object with structured schema containing:
- **pool_data**: Complete pool information with all reserves
- **asset_details**: Detailed data for specific asset (if provided)
- **risk_metrics**: Risk assessment data (if asset provided)
- **market_overview**: Pool-level market statistics
- **available_assets**: List of all available assets with key metrics

## Data Models

### Output Schema Models

#### AssetSummary
Summary of an asset's key metrics:
- Token metadata (address, symbol, name)
- APY rates (supply and borrow)
- Risk parameters (LTV, liquidation threshold)
- Market data (liquidity, debt)
- Status flags (active, borrowing enabled, collateral enabled)

#### MarketOverview
Market overview statistics:
- Total reserves count
- Total liquidity and debt in USD
- Pool utilization rate
- Base currency information

#### ComprehensiveAaveData
Comprehensive AAVE data response:
- Network information
- Complete pool data
- Market overview statistics
- Available assets list
- Optional detailed asset and risk data

### Core Data Models

#### ReserveData
Complete reserve information including:
- Token metadata (name, symbol, decimals)
- Risk parameters (LTV, liquidation thresholds)
- Market data (APY rates, liquidity)
- Status flags (active, frozen, borrowing enabled)

#### PoolData
Aggregated pool information:
- Base currency information
- List of all reserves
- Total liquidity and debt in USD
- Pool utilization rate

#### AssetData
Asset data for financial analysis:
- Token metadata and market data
- AAVE-specific APY rates
- Risk metrics and utilization rates

#### RiskData
Risk assessment metrics:
- Risk scores (1-10)
- Volatility and correlation data
- Liquidity scoring
- Protocol-specific risk factors

## Usage Examples

### Individual Tools

#### Basic Pool Data Retrieval
```python
# Get Ethereum pool data
pool_data = await get_pool_data(network="ethereum")
print(f"Found {len(pool_data.reserves)} reserves")
```

#### Asset-Specific Analysis
```python
# Get USDC reserve data
usdc_data = await get_reserve_data(
    asset_address="0xA0b86a33E6441b8c4C8C1d1Bc4C8C1d1Bc4C8C1d",
    network="ethereum"
)
print(f"USDC Supply APY: {usdc_data.liquidity_rate}%")
```

#### Risk Assessment
```python
# Get risk data for an asset
risk_data = await get_asset_risk_data(
    asset_address="0xA0b86a33E6441b8c4C8C1d1Bc4C8C1d1Bc4C8C1d",
    network="ethereum"
)
print(f"Risk Score: {risk_data.risk_score}/10")
```

### Comprehensive Tool

#### Get All AAVE Data for a Network
```python
# Get comprehensive Ethereum data
aave_data = await get_comprehensive_aave_data(network="ethereum")
print(f"Found {aave_data.market_overview.total_reserves} assets")
print(f"Total liquidity: ${aave_data.market_overview.total_liquidity_usd}")

# Access available assets
for asset in aave_data.available_assets:
    print(f"{asset.symbol}: {asset.supply_apy}% supply APY")
```

#### Get Detailed Analysis for Specific Asset
```python
# Get detailed USDC analysis
usdc_data = await get_comprehensive_aave_data(
    network="ethereum",
    asset_address="0xA0b86a33E6441b8c4C8C1d1Bc4C8C1d1Bc4C8C1d"
)
print(f"USDC Supply APY: {usdc_data.asset_details['liquidity_rate']}%")
print(f"Risk Score: {usdc_data.risk_metrics['risk_score']}/10")
```

#### Compare Assets Across Networks
```python
# Compare Ethereum vs Polygon
eth_data = await get_comprehensive_aave_data(network="ethereum")
polygon_data = await get_comprehensive_aave_data(network="polygon")

# LLM can now compare APY rates, liquidity, and risk metrics
# across different networks and assets using structured data
```

## Development

### Running Tests
```bash
uv run pytest
```

### Code Quality
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

## Architecture

### Core Components

1. **AaveClient**: Main client for AAVE API interactions
2. **Data Models**: Pydantic models for type-safe data handling
3. **Configuration**: Environment-based configuration management
4. **Caching**: Intelligent caching with configurable TTL
5. **Error Handling**: Comprehensive error hierarchy and retry logic

### Data Flow

1. **Request**: MCP tool receives request parameters
2. **Validation**: Parameters validated against Pydantic models
3. **Caching**: Check cache for existing data
4. **API Call**: Make request to AAVE API with retry logic
5. **Processing**: Transform API response to structured data
6. **Caching**: Store processed data in cache
7. **Response**: Return structured data to client

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For support and questions:
- Create an issue on GitHub
- Check the documentation
- Review the test examples

## Roadmap

- [ ] Add support for more DeFi protocols
- [ ] Implement real-time WebSocket data feeds
- [ ] Add historical data analysis
- [ ] Implement advanced risk modeling
- [ ] Add portfolio optimization tools
- [ ] Support for more blockchain networks
