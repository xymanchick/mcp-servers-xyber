import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Any

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from pydantic import Field

from mcp_server_aave.aave import (
    AaveApiError,
    AaveClient,
    AaveClientError,
    AaveError,
    get_aave_client,
)
from mcp_server_aave.schemas import (
    AAVE_ASSETS,
    AAVE_NETWORKS,
    ComprehensiveAaveData,
    NetworkAaveData,
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
async def get_available_networks(ctx: Context) -> list[str]:
    """Return a list of supported Aave networks.

    The list is sourced from the upstream Aave GraphQL API and may vary over time.
    """
    aave_client = ctx.request_context.lifespan_context["aave_client"]
    try:
        return await aave_client.get_available_networks()
    except AaveError as e:
        logger.error(f"Failed to get available networks: {e}", exc_info=True)
        raise ToolError("Failed to retrieve available networks from Aave API.") from e


@mcp_server.tool()
async def get_comprehensive_aave_data(
    ctx: Context,
    network: Annotated[
        AAVE_NETWORKS | None,
        Field(
            description="Optional: Blockchain network to query. If not provided, data for all networks will be returned."
        ),
    ] = None,
    asset_symbol: Annotated[
        AAVE_ASSETS | None,
        Field(
            description="Optional: Specific token symbol to get detailed data for. Requires 'network' to be specified."
        ),
    ] = None,
) -> ComprehensiveAaveData:
    """Fetch a simplified Aave view for agents.

    Returns a list of networks, each containing:
      - an aggregated overview (liquidity, debt, utilization)
      - a list of reserve summaries (APY, totals)

    Optional filters:
      - network: restricts to a single network (e.g. "ethereum")
      - asset_symbol: restricts reserves to the specified token symbol
    """
    if asset_symbol and not network:
        raise ToolError(
            "The 'network' parameter is required when specifying an 'asset_symbol'."
        )

    aave_client = ctx.request_context.lifespan_context["aave_client"]

    try:
        networks_to_query = (
            [network] if network else await aave_client.get_available_networks()
        )
        chain_id_map = {
            "ethereum": 1,
            "polygon": 137,
            "avalanche": 43114,
            "arbitrum": 42161,
            "optimism": 10,
        }
        chain_ids = [
            chain_id_map.get(n.lower())
            for n in networks_to_query
            if chain_id_map.get(n.lower())
        ]

        markets = await aave_client.get_markets_data(chain_ids=chain_ids)

        all_network_data = []

        for market in markets:
            # Optional filtering by network name argument
            if network and market.chain.name.lower() != network.lower():
                continue

            network_data = NetworkAaveData._from_pool_data(
                pool=market,
                asset_symbol=asset_symbol,
            )

            # If asset filter was applied and this market has no reserves, skip
            if asset_symbol and not network_data.reserves:
                continue

            all_network_data.append(network_data)

        return ComprehensiveAaveData(data=all_network_data)

    except AaveApiError as api_err:
        logger.error(f"AAVE API error: {api_err}", exc_info=True)
        raise ToolError(f"AAVE API error: {api_err}") from api_err

    except AaveClientError as client_err:
        logger.error(f"AAVE client error: {client_err}", exc_info=True)
        raise ToolError(f"AAVE client error: {client_err}") from client_err

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise ToolError("An unexpected error occurred.") from e
