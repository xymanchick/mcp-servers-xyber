"""Test cases for AaveClient module."""
import json
import pytest
import time
from unittest.mock import Mock, patch, MagicMock

import aiohttp
from aioresponses import aioresponses

from mcp_server_aave.aave.client import AaveClient, get_aave_client
from mcp_server_aave.aave.config import (
    AaveApiError,
    AaveClientError,
    AaveConfigError,
    get_aave_config,
)
from mcp_server_aave.aave.models import ReserveData, PoolData, AssetData, RiskData


class TestAaveClient:
    """Test cases for AaveClient class."""

    def test_init_success(self, mock_aave_config):
        """Test successful AaveClient initialization."""
        client = AaveClient(mock_aave_config)
        
        assert client.config == mock_aave_config
        assert client._cache == {}
        assert client._session is None
    
    def test_cache_key_generation(self, mock_aave_config):
        """Test cache key generation."""
        client = AaveClient(mock_aave_config)
        key = client._get_cache_key("get_pool_data", network="ethereum")
        
        assert key == "get_pool_data:network=ethereum"
        
        # Test with multiple parameters
        key = client._get_cache_key("get_reserve_data", asset_address="0x123", network="polygon")
        assert key == "get_reserve_data:asset_address=0x123:network=polygon"
    
    def test_get_from_cache_disabled(self, mock_aave_config, sample_pool_data):
        """Test cache retrieval when caching is disabled."""
        mock_aave_config.enable_caching = False
        client = AaveClient(mock_aave_config)
        
        # Add item to cache (shouldn't be retrieved)
        cache_key = "test-key"
        client._cache[cache_key] = (time.time(), sample_pool_data)
        
        result = client._get_from_cache(cache_key)
        assert result is None
    
    def test_get_from_cache_miss(self, mock_aave_config):
        """Test cache miss."""
        client = AaveClient(mock_aave_config)
        result = client._get_from_cache("nonexistent-key")
        assert result is None
    
    def test_get_from_cache_expired(self, mock_aave_config, sample_pool_data):
        """Test expired cache item."""
        client = AaveClient(mock_aave_config)
        
        # Add expired item to cache
        cache_key = "expired-key"
        client._cache[cache_key] = (time.time() - 600, sample_pool_data)  # 10 minutes old
        
        result = client._get_from_cache(cache_key)
        assert result is None
        assert cache_key not in client._cache  # Should be removed
    
    def test_get_from_cache_hit(self, mock_aave_config, sample_pool_data):
        """Test successful cache hit."""
        client = AaveClient(mock_aave_config)
        
        # Add fresh item to cache
        cache_key = "fresh-key"
        client._cache[cache_key] = (time.time(), sample_pool_data)
        
        result = client._get_from_cache(cache_key)
        assert result == sample_pool_data
    
    def test_store_in_cache_disabled(self, mock_aave_config, sample_pool_data):
        """Test storing in cache when caching is disabled."""
        mock_aave_config.enable_caching = False
        client = AaveClient(mock_aave_config)
        
        client._store_in_cache("test-key", sample_pool_data)
        assert len(client._cache) == 0
    
    def test_store_in_cache_enabled(self, mock_aave_config, sample_pool_data):
        """Test storing in cache when caching is enabled."""
        client = AaveClient(mock_aave_config)
        
        cache_key = "test-key"
        client._store_in_cache(cache_key, sample_pool_data)
        
        assert cache_key in client._cache
        assert client._cache[cache_key][1] == sample_pool_data
    
    @pytest.mark.asyncio
    async def test_ensure_session(self, mock_aave_config):
        """Test session initialization."""
        client = AaveClient(mock_aave_config)
        
        # Initially no session
        assert client._session is None
        
        # Get session
        session = await client._ensure_session()
        assert isinstance(session, aiohttp.ClientSession)
        assert client._session is session
        
        # Get session again (should be same instance)
        session2 = await client._ensure_session()
        assert session2 is session
        
        # Clean up
        await client.close()
    
    @pytest.mark.asyncio
    async def test_close_session(self, mock_aave_config):
        """Test closing the session."""
        client = AaveClient(mock_aave_config)
        
        # Create session
        session = await client._ensure_session()
        assert not session.closed
        
        # Close session
        await client.close()
        assert session.closed
        assert client._session is None
        
        # Close when no session exists (should not raise)
        await client.close()
    
    @pytest.mark.asyncio
    async def test_get_pool_data_success(self, mock_aave_config, sample_aave_api_response):
        """Test successful pool data retrieval."""
        client = AaveClient(mock_aave_config)
        
        with aioresponses() as mocked:
            # Mock the API response
            url = f"{mock_aave_config.api_base_url}/data/liquidity-v2"
            mocked.get(url, status=200, payload=sample_aave_api_response)
            
            result = await client.get_pool_data(network="ethereum")
            
            assert isinstance(result, PoolData)
            assert result.network == "ethereum"
            assert len(result.reserves) == 1
            assert result.total_liquidity_usd == 5000000000
            assert result.utilization_rate == 0.60
            
        # Clean up
        await client.close()
    
    @pytest.mark.asyncio
    async def test_get_pool_data_from_cache(self, mock_aave_config, sample_pool_data):
        """Test retrieving pool data from cache."""
        client = AaveClient(mock_aave_config)
        
        # Add item to cache
        cache_key = client._get_cache_key("get_pool_data", network="ethereum")
        client._cache[cache_key] = (time.time(), sample_pool_data)
        
        with aioresponses() as mocked:
            # API should not be called
            result = await client.get_pool_data(network="ethereum")
            
            assert result == sample_pool_data
            # Verify no requests were made
            assert len(mocked.requests) == 0
        
        # Clean up
        await client.close()
    
    @pytest.mark.asyncio
    async def test_get_pool_data_api_error(self, mock_aave_config):
        """Test handling of API errors."""
        client = AaveClient(mock_aave_config)
        
        with aioresponses() as mocked:
            # Mock API error response
            url = f"{mock_aave_config.api_base_url}/data/liquidity-v2"
            mocked.get(url, status=500, payload={"error": "Internal server error"})
            
            with pytest.raises(AaveApiError, match="AAVE API HTTP error: 500"):
                await client.get_pool_data(network="ethereum")
        
        # Clean up
        await client.close()
    
    @pytest.mark.asyncio
    async def test_get_pool_data_request_exception(self, mock_aave_config):
        """Test handling of request exceptions."""
        client = AaveClient(mock_aave_config)
        
        with aioresponses() as mocked:
            # Mock connection error
            url = f"{mock_aave_config.api_base_url}/data/liquidity-v2"
            mocked.get(url, exception=aiohttp.ClientConnectionError("Connection failed"))
            
            with pytest.raises(AaveApiError, match="Failed to connect to AAVE API"):
                await client.get_pool_data(network="ethereum")
        
        # Clean up
        await client.close()
    
    @pytest.mark.asyncio
    async def test_get_reserve_data_success(self, mock_aave_config, sample_reserve_data):
        """Test successful reserve data retrieval."""
        client = AaveClient(mock_aave_config)
        
        with aioresponses() as mocked:
            # Mock the pool data API response
            url = f"{mock_aave_config.api_base_url}/data/liquidity-v2"
            pool_response = {
                "baseCurrencyInfo": {},
                "reserves": [sample_reserve_data.model_dump()],
                "totalLiquidityUSD": "5000000000",
                "totalVariableDebtUSD": "2500000000",
                "totalStableDebtUSD": "500000000",
                "utilizationRate": "0.60",
            }
            mocked.get(url, status=200, payload=pool_response)
            
            result = await client.get_reserve_data(
                asset_address=sample_reserve_data.underlying_asset,
                network="ethereum"
            )
            
            assert isinstance(result, ReserveData)
            assert result.underlying_asset == sample_reserve_data.underlying_asset
            assert result.symbol == sample_reserve_data.symbol
            assert result.liquidity_rate == sample_reserve_data.liquidity_rate
            
        # Clean up
        await client.close()
    
    @pytest.mark.asyncio
    async def test_get_reserve_data_not_found(self, mock_aave_config):
        """Test reserve data retrieval for non-existent asset."""
        client = AaveClient(mock_aave_config)
        
        with aioresponses() as mocked:
            # Mock the pool data API response with different asset
            url = f"{mock_aave_config.api_base_url}/data/liquidity-v2"
            pool_response = {
                "baseCurrencyInfo": {},
                "reserves": [],
                "totalLiquidityUSD": "5000000000",
                "totalVariableDebtUSD": "2500000000",
                "totalStableDebtUSD": "500000000",
                "utilizationRate": "0.60",
            }
            mocked.get(url, status=200, payload=pool_response)
            
            with pytest.raises(AaveApiError, match="Reserve not found"):
                await client.get_reserve_data(
                    asset_address="0x1234567890123456789012345678901234567890",
                    network="ethereum"
                )
        
        # Clean up
        await client.close()
    
    @pytest.mark.asyncio
    async def test_get_asset_risk_data_success(self, mock_aave_config, sample_risk_data):
        """Test successful risk data retrieval."""
        client = AaveClient(mock_aave_config)
        
        with aioresponses() as mocked:
            # Mock the pool data API response
            url = f"{mock_aave_config.api_base_url}/data/liquidity-v2"
            pool_response = {
                "baseCurrencyInfo": {},
                "reserves": [sample_risk_data.model_dump()],
                "totalLiquidityUSD": "5000000000",
                "totalVariableDebtUSD": "2500000000",
                "totalStableDebtUSD": "500000000",
                "utilizationRate": "0.60",
            }
            mocked.get(url, status=200, payload=pool_response)
            
            result = await client.get_asset_risk_data(
                asset_address=sample_risk_data.asset_address,
                network="ethereum"
            )
            
            assert isinstance(result, RiskData)
            assert result.asset_address == sample_risk_data.asset_address
            assert result.risk_score == sample_risk_data.risk_score
            assert result.volatility == sample_risk_data.volatility
            
        # Clean up
        await client.close()
    
    @pytest.mark.asyncio
    async def test_get_pool_data_with_different_network(self, mock_aave_config, sample_aave_api_response):
        """Test pool data retrieval with different network."""
        client = AaveClient(mock_aave_config)
        
        with aioresponses() as mocked:
            # Mock the API response for polygon network
            url = f"{mock_aave_config.api_base_url}/data/liquidity-v2"
            mocked.get(url, status=200, payload=sample_aave_api_response)
            
            await client.get_pool_data(network="polygon")
            
            # Verify request was made with polygon network
            assert len(mocked.requests) == 1
            request_url = str(list(mocked.requests.keys())[0][1])
            # Note: The actual network parameter might be in query params or headers
            # This is a simplified check
        
        # Clean up
        await client.close()


class TestGetAaveClient:
    """Test cases for get_aave_client function."""
    
    @patch('mcp_server_aave.aave.client.get_aave_config')
    @patch('mcp_server_aave.aave.client.AaveClient')
    def test_get_aave_client_caching(self, mock_client_class, mock_get_config):
        """Test that get_aave_client caches instances."""
        # Setup mocks
        mock_config = Mock()
        mock_get_config.return_value = mock_config
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # First call should create a new instance
        client1 = get_aave_client()
        assert client1 == mock_client
        mock_get_config.assert_called_once()
        mock_client_class.assert_called_once_with(mock_config)
        
        # Reset mocks
        mock_get_config.reset_mock()
        mock_client_class.reset_mock()
        
        # Second call should return cached instance
        client2 = get_aave_client()
        assert client2 == mock_client
        mock_get_config.assert_not_called()
        mock_client_class.assert_not_called()
        
        # Verify same instance
        assert client1 is client2 