from __future__ import annotations

import logging
import time
from decimal import Decimal
from functools import lru_cache
from typing import Any, Dict, List, Literal

import aiohttp
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

from mcp_server_aave.aave.config import (
    AaveConfig,
    AaveApiError,
    AaveClientError,
    AaveContractError,
    get_aave_config,
)
from mcp_server_aave.aave.models import (
    ReserveData,
    PoolData,
    AssetData,
    RiskData,
)

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
    """AAVE DeFi protocol client for fetching pool data and reserve information.
    
    Handles interaction with AAVE API with retry logic and caching.
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
        
    async def close(self) -> None:
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    @retry_api_call
    async def get_pool_data(
        self, 
        network: Literal["ethereum", "polygon", "avalanche", "arbitrum", "optimism"] = "ethereum"
    ) -> PoolData:
        """Get comprehensive AAVE pool data for a specific network.
        
        Args:
            network: Blockchain network to query
            
        Returns:
            PoolData object with reserves and market information
            
        Raises:
            AaveApiError: If the API request fails
            AaveClientError: For other unexpected errors
        """
        cache_key = self._get_cache_key("get_pool_data", network=network)
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            return cached_data
        
        try:
            logger.info(f"Fetching pool data for network: {network}")
            session = await self._ensure_session()
            
            # Use AAVE API v2 endpoint (corrected path) and request JSON
            url = f"{self.config.api_base_url}/data/liquidity/v2"
            params = {"network": network}
            headers = {"Accept": "application/json"}
            
            async with session.get(url, params=params, headers=headers) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"HTTP error {response.status}: {error_text}")
                    raise AaveApiError(f"AAVE API HTTP error: {response.status}")
                
                data = await response.json()
                
                # Create PoolData object
                pool_data = PoolData.from_api_response(data, network)
                
                # Store in cache
                self._store_in_cache(cache_key, pool_data)
                
                logger.info(f"Successfully retrieved pool data for {network}: {len(pool_data.reserves)} reserves")
                return pool_data
                
        except AaveApiError:
            raise
            
        except aiohttp.ClientError as e:
            logger.error(f"Request error: {e}")
            raise AaveApiError(f"Failed to connect to AAVE API: {e}") from e
            
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            raise AaveClientError(f"Unexpected error getting pool data: {e}") from e

    @retry_api_call
    async def get_reserve_data(
        self,
        asset_address: str,
        network: Literal["ethereum", "polygon", "avalanche", "arbitrum", "optimism"] = "ethereum"
    ) -> ReserveData:
        """Get detailed reserve data for a specific asset.
        
        Args:
            asset_address: Token contract address
            network: Blockchain network
            
        Returns:
            ReserveData object with APY, liquidity, and risk parameters
            
        Raises:
            AaveApiError: If the API request fails
            AaveClientError: For other unexpected errors
        """
        cache_key = self._get_cache_key("get_reserve_data", asset_address=asset_address, network=network)
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            return cached_data
        
        try:
            logger.info(f"Fetching reserve data for {asset_address} on {network}")
            
            # Get pool data and find specific reserve
            pool_data = await self.get_pool_data(network)
            
            # Find the specific reserve
            for reserve in pool_data.reserves:
                if reserve.underlying_asset.lower() == asset_address.lower():
                    self._store_in_cache(cache_key, reserve)
                    return reserve
            
            raise AaveApiError(f"Reserve not found for asset {asset_address} on {network}")
                
        except AaveApiError:
            raise
            
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            raise AaveClientError(f"Unexpected error getting reserve data: {e}") from e

    async def get_asset_risk_data(
        self,
        asset_address: str,
        network: Literal["ethereum", "polygon", "avalanche", "arbitrum", "optimism"] = "ethereum"
    ) -> RiskData:
        """Get risk assessment data for a specific asset.
        
        Args:
            asset_address: Token contract address
            network: Blockchain network
            
        Returns:
            RiskData object with risk metrics
            
        Raises:
            AaveApiError: If the API request fails
            AaveClientError: For other unexpected errors
        """
        try:
            logger.info(f"Fetching risk data for {asset_address} on {network}")
            
            # Get reserve data
            reserve_data = await self.get_reserve_data(asset_address, network)
            
            # Mock market data (in real implementation, this would come from external APIs)
            market_data = {
                "price_usd": "1.0",
                "market_cap": "1000000000",
                "volume_24h": "10000000",
                "volatility": "0.15",
                "correlation_with_eth": "0.8",
                "risk_score": 5,
                "liquidity_score": 7,
                "concentration_risk": "0.1"
            }
            
            risk_data = RiskData.from_reserve_data(reserve_data, market_data)
            return risk_data
                
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            raise AaveClientError(f"Unexpected error getting risk data: {e}") from e
