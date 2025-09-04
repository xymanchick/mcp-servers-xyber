from __future__ import annotations

import logging
import time
from decimal import Decimal
from functools import lru_cache
from typing import Any, Dict, List, Literal

import aiohttp
from tenacity import (before_sleep_log, retry, retry_if_exception_type,
                      stop_after_attempt, wait_exponential)

from mcp_server_aave.aave.config import (AaveApiError, AaveClientError,
                                         AaveConfig, AaveContractError,
                                         get_aave_config)
from mcp_server_aave.aave.models import (AssetData, PoolData, ReserveData,
                                         RiskData)

# --- Logger Setup --- #

logger = logging.getLogger(__name__)

# --- Setup Retry Decorators --- #
retry_api_call = retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=0.5, max=10),
    retry=retry_if_exception_type((aiohttp.ClientError, AaveApiError)),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)


@lru_cache(maxsize=1)
def get_aave_client() -> AaveClient:
    """Get a cached instance of AaveClient.

    Returns:
        Initialized AaveClient instance

    Raises:
        AaveConfigError: If configuration validation fails
    """
    config = get_aave_config()
    return AaveClient(config)


class AaveClient:
    """AAVE v3 GraphQL client.

    Provides minimal, normalized market data with retry and in-memory caching.
    """

    def __init__(self, config: AaveConfig) -> None:
        """Initialize the AaveClient.

        Args:
            config: AAVE configuration settings

        Raises:
            AaveConfigError: If configuration validation fails
        """
        self.config = config
        self._cache: dict[str, tuple[float, Any]] = {}
        self._session: aiohttp.ClientSession | None = None
        self._available_networks: list[str] | None = None
        logger.info("AaveClient initialized")

    async def _ensure_session(self) -> aiohttp.ClientSession:
        """Ensure HTTP session exists.

        Returns:
            Active aiohttp ClientSession
        """
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds)
            )
        return self._session

    def _get_cache_key(self, method: str, **kwargs: Any) -> str:
        """Generate cache key for a method call.

        Args:
            method: Method name
            **kwargs: Method parameters

        Returns:
            Cache key string
        """
        params = ":".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
        return f"{method}:{params}"

    def _get_from_cache(self, cache_key: str) -> Any | None:
        """Try to get data from cache.

        Args:
            cache_key: Cache key

        Returns:
            Cached data if found and not expired, None otherwise
        """
        if not self.config.enable_caching:
            return None

        if cache_key not in self._cache:
            return None

        timestamp, data = self._cache[cache_key]
        if time.time() - timestamp > self.config.cache_ttl_seconds:
            # Cache expired
            del self._cache[cache_key]
            return None

        logger.debug(f"Cache hit for {cache_key}")
        return data

    def _store_in_cache(self, cache_key: str, data: Any) -> None:
        """Store data in cache.

        Args:
            cache_key: Cache key
            data: Data to cache
        """
        if not self.config.enable_caching:
            return

        self._cache[cache_key] = (time.time(), data)
        logger.debug(f"Stored in cache: {cache_key}")

    async def _fetch_available_networks(self) -> None:
        """Fetch and cache the list of available networks from the Aave API."""
        if self._available_networks is None:
            logger.info("Fetching available networks from Aave API...")
            try:
                session = await self._ensure_session()
                query = {
                    "query": """
                        query GetChains {
                            chains {
                                name
                            }
                        }
                    """
                }
                async with session.post(
                    self.config.api_base_url, json=query
                ) as response:
                    if response.status != 200:
                        raise AaveApiError(
                            f"Failed to fetch available networks: HTTP {response.status}"
                        )

                    data = await response.json()
                    networks = sorted(
                        [
                            chain["name"]
                            for chain in data.get("data", {}).get("chains", [])
                        ]
                    )
                    self._available_networks = networks
                    logger.info(f"Available networks: {networks}")

            except (aiohttp.ClientError, AaveApiError) as e:
                logger.error(f"Could not fetch available networks: {e}", exc_info=True)
                self._available_networks = [
                    "ethereum",
                    "polygon",
                    "avalanche",
                    "arbitrum",
                    "optimism",
                ]

    async def get_available_networks(self) -> list[str]:
        """Get a list of available networks."""
        if self._available_networks is None:
            await self._fetch_available_networks()
        return self._available_networks or []

    async def close(self) -> None:
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    @retry_api_call
    async def get_markets_data(
        self,
        chain_ids: list[int] | None = None,
    ) -> list[PoolData]:
        """Fetch markets from Aave GraphQL and normalize nested values.

        - Queries `markets` with a minimal selection set
        - Normalizes nested percentage/amount objects into flat numeric strings
        - Returns parsed `PoolData` instances

        Args:
            chain_ids: Optional list of chain IDs to query. If None, resolves from available networks.
        """
        if chain_ids is None:
            available_networks = await self.get_available_networks()
            # This is a placeholder to map network names to chain IDs.
            # A proper mapping should be implemented.
            chain_id_map = {
                "ethereum": 1,
                "polygon": 137,
                "avalanche": 43114,
                "arbitrum": 42161,
                "optimism": 10,
            }
            chain_ids = [chain_id_map.get(n.lower(), 0) for n in available_networks]
            chain_ids = [c for c in chain_ids if c != 0]

        cache_key = self._get_cache_key("get_markets_data", chain_ids=str(chain_ids))
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            return cached_data

        try:
            logger.info(f"Fetching market data for chain IDs: {chain_ids}")
            session = await self._ensure_session()

            query = {
                "query": """
                    query GetMarkets($chainIds: [ChainId!]!) {
                        markets(request: { chainIds: $chainIds }) {
                            name
                            chain { name chainId }
                            address
                            totalMarketSize
                            totalAvailableLiquidity
                            reserves(request: { orderBy: { tokenName: ASC } }) {
                                underlyingToken { address symbol decimals name }
                                aToken { symbol }
                                supplyInfo {
                                    apy { value }
                                    total { value }
                                    maxLTV { value }
                                    liquidationThreshold { value }
                                    liquidationBonus { value }
                                    canBeCollateral
                                }
                                borrowInfo {
                                    apy { value }
                                    total { amount { value } }
                                    utilizationRate { formatted }
                                    reserveFactor { value }
                                }
                                usdExchangeRate
                                isFrozen
                            }
                        }
                    }
                """,
                "variables": {"chainIds": chain_ids},
            }

            async with session.post(self.config.api_base_url, json=query) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"HTTP error {response.status}: {error_text}")
                    raise AaveApiError(f"AAVE API HTTP error: {response.status}")

                raw = await response.json()

                # Handle GraphQL errors explicitly
                if isinstance(raw, dict) and raw.get("errors"):
                    logger.error(f"GraphQL errors: {raw['errors']}")
                    raise AaveApiError(
                        "AAVE GraphQL returned errors for markets request"
                    )

                data = raw.get("data") if isinstance(raw, dict) else None
                if not data or "markets" not in data or data["markets"] is None:
                    logger.error(f"Unexpected GraphQL response: {raw}")
                    raise AaveApiError(
                        "Unexpected GraphQL response: missing markets data"
                    )

                markets_data = data.get("markets", [])
                if not isinstance(markets_data, list):
                    raise AaveApiError(
                        "Unexpected API response format: expected a list of markets"
                    )

                # Normalize nested PercentValue/TokenAmount fields into flat decimals as our models expect
                for market in markets_data:
                    reserves = market.get("reserves") or []
                    for reserve in reserves:
                        supply = reserve.get("supplyInfo") or {}
                        apy_obj = supply.get("apy") or {}
                        total_obj = supply.get("total") or {}
                        supply["apy"] = apy_obj.get("value", "0")
                        supply["total"] = total_obj.get("value", "0")
                        # risk-related optional values
                        if isinstance(supply.get("maxLTV"), dict):
                            supply["maxLTV"] = supply["maxLTV"].get("value", "0")
                        if isinstance(supply.get("liquidationThreshold"), dict):
                            supply["liquidationThreshold"] = supply[
                                "liquidationThreshold"
                            ].get("value", "0")
                        if isinstance(supply.get("liquidationBonus"), dict):
                            supply["liquidationBonus"] = supply["liquidationBonus"].get(
                                "value", "0"
                            )
                        reserve["supplyInfo"] = supply

                        borrow = reserve.get("borrowInfo")
                        if borrow is not None:
                            b_apy_obj = borrow.get("apy") or {}
                            b_total_obj = borrow.get("total") or {}
                            amount_obj = b_total_obj.get("amount") or {}
                            util_obj = borrow.get("utilizationRate") or {}
                            borrow["apy"] = b_apy_obj.get("value", "0")
                            borrow["total"] = amount_obj.get("value", "0")
                            borrow["utilizationRate"] = util_obj.get("formatted", "0")
                            if isinstance(borrow.get("reserveFactor"), dict):
                                borrow["reserveFactor"] = borrow["reserveFactor"].get(
                                    "value", "0"
                                )
                            reserve["borrowInfo"] = borrow

                pool_data = [PoolData(**item) for item in markets_data]

                self._store_in_cache(cache_key, pool_data)

                logger.info(
                    f"Successfully retrieved market data for chain IDs {chain_ids}: {len(pool_data)} markets found"
                )
                return pool_data

        except aiohttp.ClientError as e:
            logger.error(f"Request error: {e}")
            raise AaveApiError(f"Failed to connect to AAVE API: {e}") from e

        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            raise AaveClientError(f"Unexpected error getting market data: {e}") from e
