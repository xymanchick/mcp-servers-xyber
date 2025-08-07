"""Test fixtures for mcp-server-aave."""
import json
import pytest
from unittest.mock import Mock, patch
from decimal import Decimal

from mcp_server_aave.aave.config import AaveConfig
from mcp_server_aave.aave.models import ReserveData, PoolData, AssetData, RiskData


@pytest.fixture
def mock_aave_config():
    """Mock AAVE configuration for testing."""
    config = Mock(spec=AaveConfig)
    config.rpc_url = "https://eth-mainnet.g.alchemy.com/v2/test-api-key"
    config.network = "ethereum"
    config.api_base_url = "https://aave-api-v2.aave.com"
    config.timeout_seconds = 30
    config.max_retries = 3
    config.retry_delay = 1.0
    config.enable_caching = True
    config.cache_ttl_seconds = 300
    config.pool_addresses_provider = "0xB53C1a33016B2DC2fF3653530bfF1848a515c8c5"
    config.gas_limit_multiplier = 1.2
    config.max_gas_price_gwei = 100
    config.max_slippage_percent = 0.5
    config.min_health_factor = 1.1
    return config


@pytest.fixture
def sample_reserve_data():
    """Sample ReserveData instance for testing."""
    return ReserveData(
        underlying_asset="0xA0b86a33E6441b8B4b8C8C8C8C8C8C8C8C8C8C8C",
        name="USD Coin",
        symbol="USDC",
        decimals=6,
        base_ltv_as_collateral=Decimal("0.85"),
        reserve_liquidation_threshold=Decimal("0.88"),
        reserve_liquidation_bonus=Decimal("0.05"),
        reserve_factor=Decimal("0.10"),
        usage_as_collateral_enabled=True,
        borrowing_enabled=True,
        is_active=True,
        is_frozen=False,
        liquidity_index=Decimal("1.0"),
        variable_borrow_index=Decimal("1.0"),
        liquidity_rate=Decimal("0.025"),  # 2.5% APY
        variable_borrow_rate=Decimal("0.035"),  # 3.5% APY
        last_update_timestamp=1640995200,
        a_token_address="0xBcca60bB61934080951369a648Fb03DF4F96263C",
        variable_debt_token_address="0x619beb58998eD2278e08520eEe2bD7eAe0c4c8C8",
        interest_rate_strategy_address="0x8Cae0596bC1eD42dc3F04d90b0f2f1b0F1686830",
        available_liquidity=Decimal("1000000000"),  # 1B USDC
        total_scaled_variable_debt=Decimal("500000000"),  # 500M USDC
        price_in_market_reference_currency=Decimal("1.0"),
        price_oracle="0x13e3Ee699D1909E37AeEeD9570bF4e2Bd41AACC",
        variable_rate_slope_1=Decimal("0.04"),
        variable_rate_slope_2=Decimal("0.60"),
        base_variable_borrow_rate=Decimal("0.01"),
        optimal_usage_ratio=Decimal("0.80"),
        is_paused=False,
        is_siloed_borrowing=False,
        accrued_to_treasury=Decimal("0"),
        unbacked=Decimal("0"),
        isolation_mode_total_debt=Decimal("0"),
        flash_loan_enabled=True,
        debt_ceiling=Decimal("0"),
        debt_ceiling_decimals=0,
        e_mode_category_id=0,
        borrow_cap=Decimal("0"),
        supply_cap=Decimal("0"),
        borrowable_in_isolation=True,
    )


@pytest.fixture
def sample_pool_data(sample_reserve_data):
    """Sample PoolData instance for testing."""
    return PoolData(
        network="ethereum",
        base_currency_info={
            "networkBaseTokenPrice": "1800",
            "networkBaseTokenPriceDecimals": 8,
            "marketReferenceCurrencyPrice": "1",
            "marketReferenceCurrencyPriceDecimals": 8,
        },
        reserves=[sample_reserve_data],
        total_liquidity_usd=Decimal("5000000000"),  # 5B USD
        total_variable_debt_usd=Decimal("2500000000"),  # 2.5B USD
        total_stable_debt_usd=Decimal("500000000"),  # 500M USD
        utilization_rate=Decimal("0.60"),  # 60%
    )


@pytest.fixture
def sample_asset_data(sample_reserve_data):
    """Sample AssetData instance for testing."""
    return AssetData(
        address=sample_reserve_data.underlying_asset,
        symbol=sample_reserve_data.symbol,
        name=sample_reserve_data.name,
        decimals=sample_reserve_data.decimals,
        price_usd=Decimal("1.0"),
        market_cap=Decimal("50000000000"),  # 50B USD
        volume_24h=Decimal("1000000000"),  # 1B USD
        supply_apy=sample_reserve_data.liquidity_rate,
        borrow_apy=sample_reserve_data.variable_borrow_rate,
        total_supply=sample_reserve_data.available_liquidity,
        total_borrow=sample_reserve_data.total_scaled_variable_debt,
        utilization_rate=Decimal("0.50"),
        volatility=Decimal("0.15"),
        correlation_with_eth=Decimal("0.8"),
        risk_score=5,
    )


@pytest.fixture
def sample_risk_data(sample_reserve_data):
    """Sample RiskData instance for testing."""
    return RiskData(
        asset_address=sample_reserve_data.underlying_asset,
        symbol=sample_reserve_data.symbol,
        risk_score=5,
        volatility=Decimal("0.15"),
        correlation_with_eth=Decimal("0.8"),
        market_cap=Decimal("50000000000"),  # 50B USD
        liquidity_score=7,
        concentration_risk=Decimal("0.1"),
        ltv_ratio=sample_reserve_data.base_ltv_as_collateral,
        liquidation_threshold=sample_reserve_data.reserve_liquidation_threshold,
        liquidation_bonus=sample_reserve_data.reserve_liquidation_bonus,
        reserve_factor=sample_reserve_data.reserve_factor,
    )


@pytest.fixture
def sample_aave_api_response():
    """Sample AAVE API v2 response."""
    return {
        "baseCurrencyInfo": {
            "networkBaseTokenPrice": "1800",
            "networkBaseTokenPriceDecimals": 8,
            "marketReferenceCurrencyPrice": "1",
            "marketReferenceCurrencyPriceDecimals": 8,
        },
        "reserves": [
            {
                "underlyingAsset": "0xA0b86a33E6441b8B4b8C8C8C8C8C8C8C8C8C8C8C",
                "name": "USD Coin",
                "symbol": "USDC",
                "decimals": 6,
                "baseLTVAsCollateral": "0.85",
                "reserveLiquidationThreshold": "0.88",
                "reserveLiquidationBonus": "0.05",
                "reserveFactor": "0.10",
                "usageAsCollateralEnabled": True,
                "borrowingEnabled": True,
                "isActive": True,
                "isFrozen": False,
                "liquidityIndex": "1.0",
                "variableBorrowIndex": "1.0",
                "liquidityRate": "0.025",
                "variableBorrowRate": "0.035",
                "lastUpdateTimestamp": 1640995200,
                "aTokenAddress": "0xBcca60bB61934080951369a648Fb03DF4F96263C",
                "variableDebtTokenAddress": "0x619beb58998eD2278e08520eEe2bD7eAe0c4c8C8",
                "interestRateStrategyAddress": "0x8Cae0596bC1eD42dc3F04d90b0f2f1b0F1686830",
                "availableLiquidity": "1000000000",
                "totalScaledVariableDebt": "500000000",
                "priceInMarketReferenceCurrency": "1.0",
                "priceOracle": "0x13e3Ee699D1909E37AeEeD9570bF4e2Bd41AACC",
                "variableRateSlope1": "0.04",
                "variableRateSlope2": "0.60",
                "baseVariableBorrowRate": "0.01",
                "optimalUsageRatio": "0.80",
                "isPaused": False,
                "isSiloedBorrowing": False,
                "accruedToTreasury": "0",
                "unbacked": "0",
                "isolationModeTotalDebt": "0",
                "flashLoanEnabled": True,
                "debtCeiling": "0",
                "debtCeilingDecimals": 0,
                "eModeCategoryId": 0,
                "borrowCap": "0",
                "supplyCap": "0",
                "borrowableInIsolation": True,
            }
        ],
        "totalLiquidityUSD": "5000000000",
        "totalVariableDebtUSD": "2500000000",
        "totalStableDebtUSD": "500000000",
        "utilizationRate": "0.60",
    }


@pytest.fixture
def mock_response():
    """Mock aiohttp.ClientResponse object."""
    class MockResponse:
        def __init__(self, json_data, status_code):
            self.json_data = json_data
            self.status_code = status_code
            self.text = json.dumps(json_data)
            
        async def json(self):
            return self.json_data
            
        async def text(self):
            return self.text
            
        async def raise_for_status(self):
            if self.status_code != 200:
                from aiohttp import ClientResponseError
                raise ClientResponseError(
                    request_info=None,
                    history=None,
                    status=self.status_code,
                    message=f"HTTP Error: {self.status_code}"
                )
    
    return MockResponse 