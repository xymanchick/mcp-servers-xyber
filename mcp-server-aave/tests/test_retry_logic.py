"""Test cases for retry mechanism.

Test the functionality of retry_api_call decorator, including retry triggering,
retry count, exponential backoff timing and logging.
"""
import logging
import time
from unittest.mock import Mock, patch, MagicMock

import pytest
import aiohttp
from aiohttp import ClientResponseError, ClientConnectionError

from mcp_server_aave.aave.config import AaveConfig, AaveApiError, AaveClientError
from mcp_server_aave.aave.client import AaveClient
from mcp_server_aave.aave.models import PoolData


# Test data constants
TEST_NETWORKS = {
    'ethereum': 'ethereum',
    'polygon': 'polygon',
    'avalanche': 'avalanche',
}

MOCK_RESPONSES = {
    'ethereum': {
        'baseCurrencyInfo': {},
        'reserves': [],
        'totalLiquidityUSD': '5000000000',
        'totalVariableDebtUSD': '2500000000',
        'totalStableDebtUSD': '500000000',
        'utilizationRate': '0.60',
    },
    'polygon': {
        'baseCurrencyInfo': {},
        'reserves': [],
        'totalLiquidityUSD': '1000000000',
        'totalVariableDebtUSD': '500000000',
        'totalStableDebtUSD': '100000000',
        'utilizationRate': '0.50',
    },
}


class TestRetryApiCallDecorator:
    """Test the functionality of retry_api_call decorator."""
    
    @pytest.fixture
    def aave_client(self):
        """Create AaveClient instance for testing."""
        config = Mock(spec=AaveConfig)
        config.api_base_url = "https://aave-api-v2.aave.com"
        config.timeout_seconds = 30
        config.max_retries = 3
        config.retry_delay = 1.0
        config.enable_caching = False  # Disable caching for tests
        
        client = AaveClient(config)
        return client
    
    @pytest.mark.asyncio
    async def test_retry_on_connection_error_then_success(self, aave_client, caplog):
        """Test retry triggered on ClientConnectionError, eventually succeeds."""
        # Create mock response
        mock_response = Mock()
        mock_response.json = Mock(return_value=MOCK_RESPONSES['ethereum'])
        mock_response.status = 200
        
        # Mock aiohttp.ClientSession.get call count
        call_count = 0
        async def mock_get_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise ClientConnectionError("Connection failed")
            return mock_response
        
        with patch.object(aave_client, '_ensure_session') as mock_ensure_session:
            mock_session = Mock()
            mock_session.get = Mock(side_effect=mock_get_side_effect)
            mock_ensure_session.return_value = mock_session
            
            with caplog.at_level(logging.WARNING):
                result = await aave_client.get_pool_data(network="ethereum")
        
        # Verify results
        assert isinstance(result, PoolData)
        assert result.network == "ethereum"
        
        # Verify retry count (should call 3 times)
        assert call_count == 3
        
        # Verify retry logs
        retry_logs = [record for record in caplog.records if "Retrying" in record.message]
        assert len(retry_logs) == 2  # Two retry logs
        assert "get_pool_data" in retry_logs[0].message
        assert "ClientConnectionError" in retry_logs[0].message
    
    @pytest.mark.asyncio
    async def test_retry_on_aave_api_error_then_success(self, aave_client, caplog):
        """Test retry triggered on AaveApiError, eventually succeeds."""
        # Mock responses: first two fail, third succeeds
        responses = [
            Mock(status=429, json=Mock(return_value={"error": "Too many requests"})),
            Mock(status=503, json=Mock(return_value={"error": "Service unavailable"})),
            Mock(status=200, json=Mock(return_value=MOCK_RESPONSES['polygon'])),
        ]
        
        with patch.object(aave_client, '_ensure_session') as mock_ensure_session:
            mock_session = Mock()
            mock_session.get = Mock(side_effect=responses)
            mock_ensure_session.return_value = mock_session
            
            with caplog.at_level(logging.WARNING):
                result = await aave_client.get_pool_data(network="polygon")
        
        # Verify results
        assert isinstance(result, PoolData)
        assert result.network == "polygon"
        
        # Verify retry logs
        retry_logs = [record for record in caplog.records if "Retrying" in record.message]
        assert len(retry_logs) == 2
    
    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self, aave_client, caplog):
        """Test that function throws exception after exceeding max retries."""
        # Mock persistent failing requests
        with patch.object(aave_client, '_ensure_session') as mock_ensure_session:
            mock_session = Mock()
            mock_session.get = Mock(side_effect=ClientConnectionError("Connection failed"))
            mock_ensure_session.return_value = mock_session
            
            with caplog.at_level(logging.WARNING):
                with pytest.raises(AaveApiError):
                    await aave_client.get_pool_data(network="ethereum")
        
        # Verify retry count (5 retries = total 5 calls)
        assert mock_session.get.call_count == 5
        
        # Verify retry logs (should have 4 retry logs)
        retry_logs = [record for record in caplog.records if "Retrying" in record.message]
        assert len(retry_logs) == 4
    
    @pytest.mark.asyncio
    async def test_no_retry_on_parsing_error(self, aave_client, caplog):
        """Test that parsing errors (KeyError) are not retried."""
        # Create a response that will cause a KeyError during parsing
        mock_response = Mock()
        mock_response.json = Mock(return_value={"cod": 200, "reserves": None})  # Missing required fields
        mock_response.status = 200
        
        with patch.object(aave_client, '_ensure_session') as mock_ensure_session:
            mock_session = Mock()
            mock_session.get = Mock(return_value=mock_response)
            mock_ensure_session.return_value = mock_session
            
            with caplog.at_level(logging.WARNING):
                with pytest.raises(AaveClientError):
                    await aave_client.get_pool_data(network="ethereum")
        
        # Verify no retries occurred
        assert mock_session.get.call_count == 1
        
        # Verify no retry logs
        retry_logs = [record for record in caplog.records if "Retrying" in record.message]
        assert len(retry_logs) == 0
    
    @pytest.mark.asyncio
    async def test_exponential_backoff_timing(self, aave_client):
        """Test that retry uses exponential backoff for wait times."""
        # Mock time.sleep to track wait times
        sleep_times = []
        original_sleep = time.sleep
        
        def mock_sleep(seconds):
            sleep_times.append(seconds)
            # Don't actually sleep in tests
            return None
        
        # Mock persistent failing requests
        with patch('time.sleep', side_effect=mock_sleep):
            with patch.object(aave_client, '_ensure_session') as mock_ensure_session:
                mock_session = Mock()
                mock_session.get = Mock(side_effect=ClientConnectionError("Connection failed"))
                mock_ensure_session.return_value = mock_session
                
                try:
                    await aave_client.get_pool_data(network="ethereum")
                except AaveApiError:
                    pass  # Expected exception after max retries
        
        # Verify exponential backoff pattern (should increase)
        assert len(sleep_times) == 4  # 4 retries = 4 sleeps
        assert sleep_times[0] < sleep_times[1] < sleep_times[2] < sleep_times[3]
        
        # Verify multiplier is around 0.5 (with jitter)
        # First wait should be close to 0.5 seconds
        assert 0.3 <= sleep_times[0] <= 0.7 