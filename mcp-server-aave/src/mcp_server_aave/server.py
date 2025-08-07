import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Any, Literal

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from pydantic import Field

from mcp_server_aave.aave import (
    AaveClient,
    AaveError,
    AaveApiError,
    AaveClientError,
    AaveContractError,
    PoolData,
    ReserveData,
    RiskData,
    get_aave_client,
)

from mcp_server_aave.schemas import (
    AssetSummary,
    MarketOverview,
    ComprehensiveAaveData,
)

logger = logging.getLogger(__name__)

@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[dict[str, Any]]:
    """Manage server startup/shutdown. Initializes required services.
    
    Args:
        server: The FastMCP server instance
        
    Yields:
        Dictionary with initialized services
        
    Raises:
        AaveError: If service initialization fails
    """
    logger.info("Lifespan: Initializing AAVE services...")

    try:
        aave_client: AaveClient = get_aave_client()

        logger.info("Lifespan: AAVE services initialized successfully")
        yield {"aave_client": aave_client}

    except AaveError as init_err:
        logger.error(
            f"FATAL: Lifespan initialization failed: {init_err}", exc_info=True
        )
        raise init_err

    except Exception as startup_err:
        logger.error(
            f"FATAL: Unexpected error during lifespan initialization: {startup_err}",
            exc_info=True,
        )
        raise startup_err

    finally:
        try:
            await aave_client.close()
            logger.info("Lifespan: Closed AAVE client session")

        except Exception as e:
            logger.error(f"Error closing AAVE client: {e}")
                
        logger.info("Lifespan: Shutdown cleanup completed")


# --- MCP Server Initialization --- #
mcp_server = FastMCP("aave-server", lifespan=app_lifespan)

@mcp_server.tool()
async def get_comprehensive_aave_data(
    ctx: Context,
    network: Annotated[
        Literal["ethereum", "polygon", "avalanche", "arbitrum", "optimism"],
        Field(description="Blockchain network to query")
    ] = "ethereum",
    asset_address: Annotated[
        str | None, Field(description="Optional: Specific token contract address to get detailed data for")
    ] = None,
) -> ComprehensiveAaveData:
    """Get comprehensive AAVE DeFi protocol data for financial analysis and investment decisions.
    
    This tool provides all the data an agent needs to analyze AAVE investment opportunities:
    - Pool overview with all available assets
    - Detailed reserve data including APY rates
    - Risk assessment and market metrics
    - Liquidity and utilization information
    
    Args:
        network: Blockchain network to query (ethereum, polygon, avalanche, arbitrum, optimism)
        asset_address: Optional specific token address for detailed analysis
        
    Returns:
        ComprehensiveAaveData object containing:
        - pool_data: Complete pool information with all reserves
        - asset_details: Detailed data for specific asset (if provided)
        - risk_metrics: Risk assessment data (if asset provided)
        - market_overview: Pool-level market statistics
        - available_assets: List of all available assets with key metrics
        
    Raises:
        ToolError: If data retrieval fails
    """
    aave_client = ctx.request_context.lifespan_context["aave_client"]

    try:
        logger.info(f"Fetching comprehensive AAVE data for {network}" + (f" - asset: {asset_address}" if asset_address else ""))
        
        # Get pool data (always needed)
        pool_data: PoolData = await aave_client.get_pool_data(network=network)
        
        # Create market overview
        market_overview = MarketOverview(
            total_reserves =len(pool_data.reserves),
            total_liquidity_usd=str(pool_data.total_liquidity_usd),
            total_variable_debt_usd=str(pool_data.total_variable_debt_usd),
            utilization_rate=str(pool_data.utilization_rate),
            base_currency_info=pool_data.base_currency_info,
        )
        
        # Create available assets list
        available_assets = [
            AssetSummary(
                address=reserve.underlying_asset,
                symbol=reserve.symbol,
                name=reserve.name,
                supply_apy=str(reserve.liquidity_rate),
                borrow_apy=str(reserve.variable_borrow_rate),
                ltv_ratio=str(reserve.base_ltv_as_collateral),
                liquidation_threshold=str(reserve.reserve_liquidation_threshold),
                available_liquidity=str(reserve.available_liquidity),
                total_debt=str(reserve.total_scaled_variable_debt),
                is_active=reserve.is_active,
                borrowing_enabled=reserve.borrowing_enabled,
                usage_as_collateral_enabled=reserve.usage_as_collateral_enabled,
            )
            for reserve in pool_data.reserves
        ]
        
        # Initialize result
        result = ComprehensiveAaveData(
            network=network,
            pool_data=pool_data.model_dump(),
            market_overview=market_overview,
            available_assets=available_assets,
            asset_details=None,
            risk_metrics=None,
        )
        
        # If specific asset requested, get detailed data
        if asset_address:
            try:
                reserve_data: ReserveData = await aave_client.get_reserve_data(asset_address, network)
                risk_data: RiskData = await aave_client.get_asset_risk_data(asset_address, network)
                
                result.asset_details = reserve_data.model_dump()
                result.risk_metrics = risk_data.model_dump()
                
                logger.info(f"Successfully retrieved detailed data for {asset_address} on {network}")
                
            except AaveApiError as e:
                logger.warning(f"Could not get detailed data for {asset_address}: {e}")
                # Keep asset_details and risk_metrics as None
        
        logger.info(f"Successfully retrieved comprehensive AAVE data for {network}: {len(pool_data.reserves)} reserves")
        return result

    except AaveApiError as api_err:
        logger.error(f"AAVE API error: {api_err}")
        raise ToolError(f"AAVE API error: {api_err}") from api_err

    except AaveClientError as client_err:
        logger.error(f"AAVE client error: {client_err}")
        raise ToolError(f"AAVE client error: {client_err}") from client_err

    except Exception as e:
        logger.error(f"Unexpected error processing tool get_comprehensive_aave_data: {e}", exc_info=True)
        raise ToolError(
            "An unexpected error occurred processing AAVE comprehensive data request"
        ) from e
