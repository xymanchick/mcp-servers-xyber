"""AAVE DeFi protocol data models with modern Python 3.12+ features."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, List, Literal

from pydantic import BaseModel, Field


class ReserveData(BaseModel):
    """AAVE reserve data model."""
    
    underlying_asset: str = Field(description="Token contract address")
    name: str = Field(description="Token name")
    symbol: str = Field(description="Token symbol")
    decimals: int = Field(description="Token decimals")
    
    # Risk parameters
    base_ltv_as_collateral: Decimal = Field(description="Loan-to-value ratio")
    reserve_liquidation_threshold: Decimal = Field(description="Liquidation threshold")
    reserve_liquidation_bonus: Decimal = Field(description="Liquidation bonus")
    reserve_factor: Decimal = Field(description="Reserve factor")
    
    # Status flags
    usage_as_collateral_enabled: bool = Field(description="Can be used as collateral")
    borrowing_enabled: bool = Field(description="Borrowing is enabled")
    is_active: bool = Field(description="Reserve is active")
    is_frozen: bool = Field(description="Reserve is frozen")
    
    # Market data
    liquidity_index: Decimal = Field(description="Liquidity index")
    variable_borrow_index: Decimal = Field(description="Variable borrow index")
    liquidity_rate: Decimal = Field(description="Liquidity rate (APY)")
    variable_borrow_rate: Decimal = Field(description="Variable borrow rate (APY)")
    last_update_timestamp: int = Field(description="Last update timestamp")
    
    # Token addresses
    a_token_address: str = Field(description="aToken contract address")
    variable_debt_token_address: str = Field(description="Variable debt token address")
    interest_rate_strategy_address: str = Field(description="Interest rate strategy address")
    
    # Market data
    available_liquidity: Decimal = Field(description="Available liquidity")
    total_scaled_variable_debt: Decimal = Field(description="Total scaled variable debt")
    price_in_market_reference_currency: Decimal = Field(description="Price in market reference currency")
    price_oracle: str = Field(description="Price oracle address")
    
    # Interest rate parameters
    variable_rate_slope_1: Decimal = Field(description="Variable rate slope 1")
    variable_rate_slope_2: Decimal = Field(description="Variable rate slope 2")
    base_variable_borrow_rate: Decimal = Field(description="Base variable borrow rate")
    optimal_usage_ratio: Decimal = Field(description="Optimal usage ratio")
    
    # V3 specific fields
    is_paused: bool = Field(default=False, description="Pool is paused")
    is_siloed_borrowing: bool = Field(default=False, description="Asset is siloed for borrowing")
    accrued_to_treasury: Decimal = Field(default=Decimal("0"), description="Amount accrued to treasury")
    unbacked: Decimal = Field(default=Decimal("0"), description="Amount of unbacked aTokens")
    isolation_mode_total_debt: Decimal = Field(default=Decimal("0"), description="Isolation mode total debt")
    flash_loan_enabled: bool = Field(default=True, description="Flash loan enabled")
    debt_ceiling: Decimal = Field(default=Decimal("0"), description="Debt ceiling")
    debt_ceiling_decimals: int = Field(default=0, description="Debt ceiling decimals")
    e_mode_category_id: int = Field(default=0, description="eMode category ID")
    borrow_cap: Decimal = Field(default=Decimal("0"), description="Borrow cap")
    supply_cap: Decimal = Field(default=Decimal("0"), description="Supply cap")
    borrowable_in_isolation: bool = Field(default=True, description="Borrowable in isolation")
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> ReserveData:
        """Create a ReserveData instance from API response."""
        return cls(**data)


class PoolData(BaseModel):
    """AAVE pool data model."""
    
    network: str = Field(description="Blockchain network")
    base_currency_info: Dict[str, Any] = Field(description="Base currency information")
    reserves: List[ReserveData] = Field(description="List of reserves")
    total_liquidity_usd: Decimal = Field(description="Total liquidity in USD")
    total_variable_debt_usd: Decimal = Field(description="Total variable debt in USD")
    total_stable_debt_usd: Decimal = Field(description="Total stable debt in USD")
    utilization_rate: Decimal = Field(description="Pool utilization rate")
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any], network: str) -> PoolData:
        """Create a PoolData instance from API response."""
        return cls(
            network=network,
            base_currency_info=data.get("baseCurrencyInfo", {}),
            reserves=[ReserveData.from_api_response(reserve) for reserve in data.get("reserves", [])],
            total_liquidity_usd=Decimal(str(data.get("totalLiquidityUSD", "0"))),
            total_variable_debt_usd=Decimal(str(data.get("totalVariableDebtUSD", "0"))),
            total_stable_debt_usd=Decimal(str(data.get("totalStableDebtUSD", "0"))),
            utilization_rate=Decimal(str(data.get("utilizationRate", "0"))),
        )


class AssetData(BaseModel):
    """Asset data for financial analysis."""
    
    address: str = Field(description="Token contract address")
    symbol: str = Field(description="Token symbol")
    name: str = Field(description="Token name")
    decimals: int = Field(description="Token decimals")
    price_usd: Decimal = Field(description="Price in USD")
    market_cap: Decimal = Field(description="Market capitalization")
    volume_24h: Decimal = Field(description="24-hour trading volume")
    
    # AAVE specific data
    supply_apy: Decimal = Field(description="Supply APY")
    borrow_apy: Decimal = Field(description="Borrow APY")
    total_supply: Decimal = Field(description="Total supply")
    total_borrow: Decimal = Field(description="Total borrow")
    utilization_rate: Decimal = Field(description="Utilization rate")
    
    # Risk metrics
    volatility: Decimal = Field(description="Price volatility")
    correlation_with_eth: Decimal = Field(description="Correlation with ETH")
    risk_score: int = Field(description="Risk score (1-10)")
    
    @classmethod
    def from_reserve_data(cls, reserve: ReserveData, market_data: Dict[str, Any]) -> AssetData:
        """Create AssetData from ReserveData and market data."""
        return cls(
            address=reserve.underlying_asset,
            symbol=reserve.symbol,
            name=reserve.name,
            decimals=reserve.decimals,
            price_usd=Decimal(str(market_data.get("price_usd", "0"))),
            market_cap=Decimal(str(market_data.get("market_cap", "0"))),
            volume_24h=Decimal(str(market_data.get("volume_24h", "0"))),
            supply_apy=reserve.liquidity_rate,
            borrow_apy=reserve.variable_borrow_rate,
            total_supply=reserve.available_liquidity,
            total_borrow=reserve.total_scaled_variable_debt,
            utilization_rate=reserve.total_scaled_variable_debt / reserve.available_liquidity if reserve.available_liquidity > 0 else Decimal("0"),
            volatility=Decimal(str(market_data.get("volatility", "0"))),
            correlation_with_eth=Decimal(str(market_data.get("correlation_with_eth", "0"))),
            risk_score=int(market_data.get("risk_score", 5)),
        )


class RiskData(BaseModel):
    """Risk assessment data."""
    
    asset_address: str = Field(description="Token contract address")
    symbol: str = Field(description="Token symbol")
    risk_score: int = Field(description="Risk score (1-10)")
    volatility: Decimal = Field(description="Price volatility")
    correlation_with_eth: Decimal = Field(description="Correlation with ETH")
    market_cap: Decimal = Field(description="Market capitalization")
    liquidity_score: int = Field(description="Liquidity score (1-10)")
    concentration_risk: Decimal = Field(description="Concentration risk")
    
    # AAVE specific risk factors
    ltv_ratio: Decimal = Field(description="Loan-to-value ratio")
    liquidation_threshold: Decimal = Field(description="Liquidation threshold")
    liquidation_bonus: Decimal = Field(description="Liquidation bonus")
    reserve_factor: Decimal = Field(description="Reserve factor")
    
    @classmethod
    def from_reserve_data(cls, reserve: ReserveData, market_data: Dict[str, Any]) -> RiskData:
        """Create RiskData from ReserveData and market data."""
        return cls(
            asset_address=reserve.underlying_asset,
            symbol=reserve.symbol,
            risk_score=int(market_data.get("risk_score", 5)),
            volatility=Decimal(str(market_data.get("volatility", "0"))),
            correlation_with_eth=Decimal(str(market_data.get("correlation_with_eth", "0"))),
            market_cap=Decimal(str(market_data.get("market_cap", "0"))),
            liquidity_score=int(market_data.get("liquidity_score", 5)),
            concentration_risk=Decimal(str(market_data.get("concentration_risk", "0"))),
            ltv_ratio=reserve.base_ltv_as_collateral,
            liquidation_threshold=reserve.reserve_liquidation_threshold,
            liquidation_bonus=reserve.reserve_liquidation_bonus,
            reserve_factor=reserve.reserve_factor,
        )
    