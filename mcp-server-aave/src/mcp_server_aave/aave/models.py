"""AAVE DeFi protocol data models with modern Python 3.12+ features."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, List, Literal

from pydantic import BaseModel, ConfigDict, Field


class AToken(BaseModel):
    """AToken data model."""

    symbol: str


class SupplyInfo(BaseModel):
    """Supply info data model."""

    apy: Decimal
    total: Decimal


class BorrowInfo(BaseModel):
    """Borrow info data model."""

    apy: Decimal
    total: Decimal
    utilization_rate: str = Field(alias="utilizationRate")

    model_config = ConfigDict(populate_by_name=True)


class UnderlyingToken(BaseModel):
    """Underlying token data model."""

    symbol: str
    name: str
    decimals: int
    address: str


class ReserveData(BaseModel):
    """AAVE reserve data model."""

    underlying_token: UnderlyingToken = Field(alias="underlyingToken")
    a_token: AToken = Field(alias="aToken")
    supply_info: SupplyInfo = Field(alias="supplyInfo")
    borrow_info: BorrowInfo | None = Field(alias="borrowInfo")
    usd_exchange_rate: Decimal = Field(alias="usdExchangeRate")
    is_frozen: bool = Field(alias="isFrozen")

    model_config = ConfigDict(populate_by_name=True)


class Chain(BaseModel):
    """Chain data model."""

    name: str
    chain_id: int = Field(alias="chainId")

    model_config = ConfigDict(populate_by_name=True)


class PoolData(BaseModel):
    """AAVE pool data model."""

    name: str
    address: str
    chain: Chain
    icon: str | None = None
    total_market_size: Decimal = Field(alias="totalMarketSize")
    total_available_liquidity: Decimal = Field(alias="totalAvailableLiquidity")
    reserves: list[ReserveData]

    model_config = ConfigDict(populate_by_name=True)


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
    def from_reserve_data(
        cls, reserve: ReserveData, market_data: dict[str, Any]
    ) -> AssetData:
        """Create AssetData from ReserveData and market data."""
        return cls(
            address=reserve.underlying_token.address,
            symbol=reserve.underlying_token.symbol,
            name=reserve.underlying_token.name,
            decimals=reserve.underlying_token.decimals,
            price_usd=Decimal(str(market_data.get("price_usd", "0"))),
            market_cap=Decimal(str(market_data.get("market_cap", "0"))),
            volume_24h=Decimal(str(market_data.get("volume_24h", "0"))),
            supply_apy=reserve.supply_info.apy,
            borrow_apy=reserve.borrow_info.apy if reserve.borrow_info else Decimal("0"),
            total_supply=reserve.supply_info.total,
            total_borrow=reserve.borrow_info.total
            if reserve.borrow_info
            else Decimal("0"),
            utilization_rate=Decimal(reserve.borrow_info.utilization_rate)
            if reserve.borrow_info
            else Decimal("0"),
            volatility=Decimal(str(market_data.get("volatility", "0"))),
            correlation_with_eth=Decimal(
                str(market_data.get("correlation_with_eth", "0"))
            ),
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

    @classmethod
    def from_reserve_data(
        cls, reserve: ReserveData, market_data: dict[str, Any]
    ) -> RiskData:
        """Create RiskData from ReserveData and market data."""
        return cls(
            asset_address=reserve.underlying_token.address,
            symbol=reserve.underlying_token.symbol,
            risk_score=int(market_data.get("risk_score", 5)),
            volatility=Decimal(str(market_data.get("volatility", "0"))),
            correlation_with_eth=Decimal(
                str(market_data.get("correlation_with_eth", "0"))
            ),
            market_cap=Decimal(str(market_data.get("market_cap", "0"))),
            liquidity_score=int(market_data.get("liquidity_score", 5)),
            concentration_risk=Decimal(str(market_data.get("concentration_risk", "0"))),
        )
