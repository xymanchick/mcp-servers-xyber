from typing import Any

from pydantic import BaseModel, Field

from mcp_server_aave.aave.models import PoolData, ReserveData

# --- Output Schema Models --- #


class AssetSummary(BaseModel):
    """Summary of an asset's key metrics."""

    address: str = Field(description="Token contract address")
    symbol: str = Field(description="Token symbol")
    name: str = Field(description="Token name")
    supply_apy: str = Field(description="Supply APY rate")
    borrow_apy: str = Field(description="Borrow APY rate")
    total_supply: str = Field(description="Total supply")
    total_debt: str = Field(description="Total debt")

    @classmethod
    def from_reserve(cls, reserve: ReserveData) -> "AssetSummary":
        """Build an AssetSummary from a ReserveData instance."""
        borrow_apy = str(reserve.borrow_info.apy) if reserve.borrow_info else "0"
        total_debt = str(reserve.borrow_info.total) if reserve.borrow_info else "0"
        return cls(
            address=reserve.underlying_token.address,
            symbol=reserve.underlying_token.symbol,
            name=reserve.underlying_token.name,
            supply_apy=str(reserve.supply_info.apy),
            borrow_apy=borrow_apy,
            total_supply=str(reserve.supply_info.total),
            total_debt=total_debt,
        )


class MarketOverview(BaseModel):
    """Market overview statistics."""

    total_reserves: int = Field(description="Total number of reserves")
    total_liquidity_usd: str = Field(description="Total liquidity in USD")
    total_variable_debt_usd: str = Field(description="Total variable debt in USD")
    utilization_rate: str = Field(description="Pool utilization rate")
    base_currency_info: dict[str, Any] = Field(description="Base currency information")


class NetworkAaveData(BaseModel):
    """Simplified network view with overview and reserves."""

    network: str = Field(description="Blockchain network")
    overview: MarketOverview = Field(description="Aggregated market overview")
    reserves: list[AssetSummary] = Field(description="List of reserves summaries")

    @classmethod
    def _from_pool_data(
        cls,
        pool: PoolData,
        asset_address: str | None = None,
    ) -> "NetworkAaveData":
        """Construct a NetworkAaveData from a PoolData, with optional asset filtering."""
        # Filter reserves if asset specified
        filtered_reserves: list[ReserveData] = []
        for reserve in pool.reserves:
            if (
                asset_address
                and reserve.underlying_token.address.lower() != asset_address.lower()
            ):
                continue
            filtered_reserves.append(reserve)

        # If an asset filter was given but no match, return an empty set for this market
        if asset_address and not filtered_reserves:
            return cls(
                network=pool.chain.name,
                overview=MarketOverview(
                    total_reserves=0,
                    total_liquidity_usd=str(pool.total_available_liquidity),
                    total_variable_debt_usd=str(pool.total_market_size),
                    utilization_rate=str(
                        pool.total_market_size / pool.total_available_liquidity
                    )
                    if pool.total_available_liquidity > 0
                    else "0",
                    base_currency_info={"symbol": "USD", "decimals": 2},
                ),
                reserves=[],
            )

        # Build summaries
        summaries: list[AssetSummary] = [
            AssetSummary.from_reserve(r) for r in (filtered_reserves or pool.reserves)
        ]

        overview = MarketOverview(
            total_reserves=len(summaries),
            total_liquidity_usd=str(pool.total_available_liquidity),
            total_variable_debt_usd=str(pool.total_market_size),
            utilization_rate=str(
                pool.total_market_size / pool.total_available_liquidity
            )
            if pool.total_available_liquidity > 0
            else "0",
            base_currency_info={"symbol": "USD", "decimals": 2},
        )

        return cls(
            network=pool.chain.name,
            overview=overview,
            reserves=summaries,
        )


class ComprehensiveAaveData(BaseModel):
    """Comprehensive AAVE data response, potentially spanning multiple networks."""

    data: list[NetworkAaveData] = Field(
        description="List of Aave data for each network"
    )
