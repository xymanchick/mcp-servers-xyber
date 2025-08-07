"""Test cases for MCP server and tools."""
import json
import pytest
from unittest.mock import Mock, patch, AsyncMock

from fastmcp import Context
from fastmcp.exceptions import ToolError

from mcp_server_aave.server import mcp_server, app_lifespan
from mcp_server_aave.aave import AaveApiError, AaveClientError
from mcp_server_aave.aave.models import PoolData, ReserveData, RiskData
from mcp_server_aave.schemas import ComprehensiveAaveData, MarketOverview, AssetSummary


class TestGetComprehensiveAaveDataTool:
    """Test cases for get_comprehensive_aave_data tool."""
    
    @pytest.fixture
    def mock_context(self):
        """Create a mock MCP context."""
        context = Mock(spec=Context)
        context.request_context = Mock()
        context.request_context.lifespan_context = {
            "aave_client": Mock()
        }
        return context
    
    @pytest.mark.asyncio
    async def test_get_comprehensive_aave_data_success(self, mock_context, sample_pool_data, sample_reserve_data, sample_risk_data):
        """Test successful comprehensive AAVE data retrieval."""
        # Setup mock AAVE client
        aave_client = mock_context.request_context.lifespan_context["aave_client"]
        aave_client.get_pool_data = AsyncMock(return_value=sample_pool_data)
        aave_client.get_reserve_data = AsyncMock(return_value=sample_reserve_data)
        aave_client.get_asset_risk_data = AsyncMock(return_value=sample_risk_data)

        # Call the comprehensive tool
        result = await mcp_server.tools["get_comprehensive_aave_data"].handler(
            mock_context, network="ethereum", asset_address=sample_reserve_data.underlying_asset
        )
        
        # Verify result
        assert isinstance(result, ComprehensiveAaveData)
        assert result.network == "ethereum"
        assert result.market_overview.total_reserves == 1
        assert len(result.available_assets) == 1
        assert result.asset_details is not None
        assert result.risk_metrics is not None
        
        # Verify AAVE client was called correctly
        aave_client.get_pool_data.assert_called_once_with(network="ethereum")
        aave_client.get_reserve_data.assert_called_once_with(sample_reserve_data.underlying_asset, "ethereum")
        aave_client.get_asset_risk_data.assert_called_once_with(sample_reserve_data.underlying_asset, "ethereum")
    
    @pytest.mark.asyncio
    async def test_get_comprehensive_aave_data_no_asset(self, mock_context, sample_pool_data):
        """Test comprehensive AAVE data retrieval without specific asset."""
        # Setup mock AAVE client
        aave_client = mock_context.request_context.lifespan_context["aave_client"]
        aave_client.get_pool_data = AsyncMock(return_value=sample_pool_data)

        # Call the comprehensive tool without asset_address
        result = await mcp_server.tools["get_comprehensive_aave_data"].handler(
            mock_context, network="ethereum"
        )
        
        # Verify result
        assert isinstance(result, ComprehensiveAaveData)
        assert result.network == "ethereum"
        assert result.market_overview.total_reserves == 1
        assert len(result.available_assets) == 1
        assert result.asset_details is None
        assert result.risk_metrics is None
        
        # Verify only pool data was called
        aave_client.get_pool_data.assert_called_once_with(network="ethereum")
        aave_client.get_reserve_data.assert_not_called()
        aave_client.get_asset_risk_data.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_get_comprehensive_aave_data_api_error(self, mock_context):
        """Test handling of API errors."""
        # Setup mock AAVE client to raise API error
        aave_client = mock_context.request_context.lifespan_context["aave_client"]
        aave_client.get_pool_data = AsyncMock(side_effect=AaveApiError("API key invalid"))

        # Call the tool and expect error
        with pytest.raises(ToolError, match="AAVE API error: API key invalid"):
            await mcp_server.tools["get_comprehensive_aave_data"].handler(
                mock_context, network="ethereum"
            )
    
    @pytest.mark.asyncio
    async def test_get_comprehensive_aave_data_client_error(self, mock_context):
        """Test handling of client errors."""
        # Setup mock AAVE client to raise client error
        aave_client = mock_context.request_context.lifespan_context["aave_client"]
        aave_client.get_pool_data = AsyncMock(side_effect=AaveClientError("Failed to parse data"))

        # Call the tool and expect error
        with pytest.raises(ToolError, match="AAVE client error: Failed to parse data"):
            await mcp_server.tools["get_comprehensive_aave_data"].handler(
                mock_context, network="ethereum"
            )
    
    @pytest.mark.asyncio
    async def test_get_comprehensive_aave_data_unexpected_error(self, mock_context):
        """Test handling of unexpected errors."""
        # Setup mock AAVE client to raise unexpected error
        aave_client = mock_context.request_context.lifespan_context["aave_client"]
        aave_client.get_pool_data = AsyncMock(side_effect=ValueError("Unexpected error"))

        # Call the tool and expect error
        with pytest.raises(ToolError, match="An unexpected error occurred processing AAVE comprehensive data request"):
            await mcp_server.tools["get_comprehensive_aave_data"].handler(
                mock_context, network="ethereum"
            )


class TestGetPoolDataTool:
    """Test cases for get_pool_data tool."""
    
    @pytest.fixture
    def mock_context(self):
        """Create a mock MCP context."""
        context = Mock(spec=Context)
        context.request_context = Mock()
        context.request_context.lifespan_context = {
            "aave_client": Mock()
        }
        return context
    
    @pytest.mark.asyncio
    async def test_get_pool_data_success(self, mock_context, sample_pool_data):
        """Test successful pool data retrieval."""
        # Setup mock AAVE client
        aave_client = mock_context.request_context.lifespan_context["aave_client"]
        aave_client.get_pool_data = AsyncMock(return_value=sample_pool_data)

        # Call the tool
        result = await mcp_server.tools["get_pool_data"].handler(
            mock_context, network="ethereum"
        )
        
        # Verify result
        assert isinstance(result, dict)
        assert result["network"] == "ethereum"
        assert len(result["reserves"]) == 1
        
        # Verify AAVE client was called correctly
        aave_client.get_pool_data.assert_called_once_with(network="ethereum")
    
    @pytest.mark.asyncio
    async def test_get_pool_data_api_error(self, mock_context):
        """Test handling of API errors."""
        # Setup mock AAVE client to raise API error
        aave_client = mock_context.request_context.lifespan_context["aave_client"]
        aave_client.get_pool_data = AsyncMock(side_effect=AaveApiError("API key invalid"))

        # Call the tool and expect error
        with pytest.raises(ToolError, match="AAVE API error: API key invalid"):
            await mcp_server.tools["get_pool_data"].handler(
                mock_context, network="ethereum"
            )


class TestGetReserveDataTool:
    """Test cases for get_reserve_data tool."""
    
    @pytest.fixture
    def mock_context(self):
        """Create a mock MCP context."""
        context = Mock(spec=Context)
        context.request_context = Mock()
        context.request_context.lifespan_context = {
            "aave_client": Mock()
        }
        return context
    
    @pytest.mark.asyncio
    async def test_get_reserve_data_success(self, mock_context, sample_reserve_data):
        """Test successful reserve data retrieval."""
        # Setup mock AAVE client
        aave_client = mock_context.request_context.lifespan_context["aave_client"]
        aave_client.get_reserve_data = AsyncMock(return_value=sample_reserve_data)

        # Call the tool
        result = await mcp_server.tools["get_reserve_data"].handler(
            mock_context, asset_address=sample_reserve_data.underlying_asset, network="ethereum"
        )
        
        # Verify result
        assert isinstance(result, dict)
        assert result["underlying_asset"] == sample_reserve_data.underlying_asset
        assert result["symbol"] == sample_reserve_data.symbol
        
        # Verify AAVE client was called correctly
        aave_client.get_reserve_data.assert_called_once_with(
            asset_address=sample_reserve_data.underlying_asset, network="ethereum"
        )


class TestGetAssetRiskDataTool:
    """Test cases for get_asset_risk_data tool."""
    
    @pytest.fixture
    def mock_context(self):
        """Create a mock MCP context."""
        context = Mock(spec=Context)
        context.request_context = Mock()
        context.request_context.lifespan_context = {
            "aave_client": Mock()
        }
        return context
    
    @pytest.mark.asyncio
    async def test_get_asset_risk_data_success(self, mock_context, sample_risk_data):
        """Test successful risk data retrieval."""
        # Setup mock AAVE client
        aave_client = mock_context.request_context.lifespan_context["aave_client"]
        aave_client.get_asset_risk_data = AsyncMock(return_value=sample_risk_data)

        # Call the tool
        result = await mcp_server.tools["get_asset_risk_data"].handler(
            mock_context, asset_address=sample_risk_data.asset_address, network="ethereum"
        )
        
        # Verify result
        assert isinstance(result, dict)
        assert result["asset_address"] == sample_risk_data.asset_address
        assert result["risk_score"] == sample_risk_data.risk_score
        
        # Verify AAVE client was called correctly
        aave_client.get_asset_risk_data.assert_called_once_with(
            asset_address=sample_risk_data.asset_address, network="ethereum"
        )


class TestAppLifespan:
    """Test cases for app_lifespan context manager."""
    
    @pytest.mark.asyncio
    async def test_app_lifespan_success(self):
        """Test successful lifespan initialization."""
        # Mock server
        server = Mock()
        
        # Mock get_aave_client
        with patch('mcp_server_aave.server.get_aave_client') as mock_get_client:
            mock_client = Mock()
            mock_get_client.return_value = mock_client
            
            # Use lifespan context manager
            async with app_lifespan(server) as context:
                # Verify context has AAVE client
                assert "aave_client" in context
                assert context["aave_client"] == mock_client
                
                # Verify client was initialized
                mock_get_client.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_app_lifespan_aave_error(self):
        """Test lifespan with AAVE initialization error."""
        # Mock server
        server = Mock()
        
        # Mock get_aave_client to raise error
        with patch('mcp_server_aave.server.get_aave_client') as mock_get_client:
            mock_get_client.side_effect = AaveApiError("Failed to initialize")
            
            # Use lifespan context manager and expect error
            with pytest.raises(AaveApiError, match="Failed to initialize"):
                async with app_lifespan(server) as context:
                    pass  # Should not reach here
    
    @pytest.mark.asyncio
    async def test_app_lifespan_unexpected_error(self):
        """Test lifespan with unexpected initialization error."""
        # Mock server
        server = Mock()
        
        # Mock get_aave_client to raise unexpected error
        with patch('mcp_server_aave.server.get_aave_client') as mock_get_client:
            mock_get_client.side_effect = Exception("Unexpected initialization error")
            
            # Use lifespan context manager and expect error
            with pytest.raises(Exception, match="Unexpected initialization error"):
                async with app_lifespan(server) as context:
                    pass  # Should not reach here 