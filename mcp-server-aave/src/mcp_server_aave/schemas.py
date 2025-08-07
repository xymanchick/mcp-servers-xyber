from pydantic import BaseModel, Field
from typing import Any

# --- Output Schema Models --- #

class AssetSummary(BaseModel):
    """Summary of an asset's key metrics."""
    address: str = Field(description="Token contract address")
    symbol: str = Field(description="Token symbol")
    name: str = Field(description="Token name")
    supply_apy: str = Field(description="Supply APY rate")
    borrow_apy: str = Field(description="Borrow APY rate")
    ltv_ratio: str = Field(description="Loan-to-value ratio")
    liquidation_threshold: str = Field(description="Liquidation threshold")
    available_liquidity: str = Field(description="Available liquidity")
    total_debt: str = Field(description="Total debt")
    is_active: bool = Field(description="Whether the asset is active")
    borrowing_enabled: bool = Field(description="Whether borrowing is enabled")
    usage_as_collateral_enabled: bool = Field(description="Whether asset can be used as collateral")


class MarketOverview(BaseModel):
    """Market overview statistics."""
    total_reserves: int = Field(description="Total number of reserves")
    total_liquidity_usd: str = Field(description="Total liquidity in USD")
    total_variable_debt_usd: str = Field(description="Total variable debt in USD")
    utilization_rate: str = Field(description="Pool utilization rate")
    base_currency_info: dict[str, Any] = Field(description="Base currency information")


class ComprehensiveAaveData(BaseModel):
    """Comprehensive AAVE data response."""
    network: str = Field(description="Blockchain network")
    pool_data: dict[str, Any] = Field(description="Complete pool data")
    market_overview: MarketOverview = Field(description="Market overview statistics")
    available_assets: list[AssetSummary] = Field(description="List of available assets with key metrics")
    asset_details: dict[str, Any] | None = Field(description="Detailed data for specific asset (if provided)")
    risk_metrics: dict[str, Any] | None = Field(description="Risk assessment data (if asset provided)")
