"""Test cases for MCP routers."""

from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import Request
from fastmcp.exceptions import ToolError
from mcp_server_aave.mcp_routers.available_networks import get_available_networks
from mcp_server_aave.mcp_routers.comprehensive_data import (
    ComprehensiveAaveDataRequest,
    get_comprehensive_aave_data,
)

from mcp_server_aave.aave import AaveApiError, AaveClientError
from mcp_server_aave.schemas import ComprehensiveAaveData


class TestGetAvailableNetworks:
    """Test cases for get_available_networks router."""

    @pytest.fixture
    def mock_request(self):
        """Create a mock FastAPI request."""
        request = Mock(spec=Request)
        request.app = Mock()
        request.app.state = Mock()
        request.app.state.aave_client = Mock()
        return request

    @pytest.mark.asyncio
    async def test_get_available_networks_success(self, mock_request):
        """Test successful retrieval of available networks."""
        # Setup mock client
        mock_request.app.state.aave_client.get_available_networks = AsyncMock(
            return_value=["ethereum", "polygon", "avalanche"]
        )

        # Call the router
        result = await get_available_networks(mock_request)

        # Verify result
        assert result == ["ethereum", "polygon", "avalanche"]
        mock_request.app.state.aave_client.get_available_networks.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_available_networks_error(self, mock_request):
        """Test handling of API errors."""
        # Setup mock client to raise error
        mock_request.app.state.aave_client.get_available_networks = AsyncMock(
            side_effect=AaveApiError("API error")
        )

        # Call the router and expect error
        with pytest.raises(ToolError, match="Failed to retrieve available networks"):
            await get_available_networks(mock_request)


class TestGetComprehensiveAaveData:
    """Test cases for get_comprehensive_aave_data router."""

    @pytest.fixture
    def mock_request(self):
        """Create a mock FastAPI request."""
        request = Mock(spec=Request)
        request.app = Mock()
        request.app.state = Mock()
        request.app.state.aave_client = Mock()
        return request

    @pytest.mark.asyncio
    async def test_get_comprehensive_aave_data_success(
        self, mock_request, sample_pool_data
    ):
        """Test successful comprehensive AAVE data retrieval."""
        # Setup mock client
        mock_request.app.state.aave_client.get_markets_data = AsyncMock(
            return_value=[sample_pool_data]
        )
        mock_request.app.state.aave_client.get_available_networks = AsyncMock(
            return_value=["ethereum"]
        )

        # Create request data
        request_data = ComprehensiveAaveDataRequest(
            networks=["ethereum"], asset_symbols=None
        )

        # Call the router
        result = await get_comprehensive_aave_data(request_data, mock_request)

        # Verify result
        assert isinstance(result, ComprehensiveAaveData)
        assert len(result.data) > 0
        assert result.data[0].network == "Ethereum"

        # Verify client was called
        mock_request.app.state.aave_client.get_markets_data.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_comprehensive_aave_data_with_asset_filter(
        self, mock_request, sample_pool_data, sample_reserve_data
    ):
        """Test comprehensive AAVE data retrieval with asset filter."""
        # Setup mock client
        mock_request.app.state.aave_client.get_markets_data = AsyncMock(
            return_value=[sample_pool_data]
        )
        mock_request.app.state.aave_client.get_available_networks = AsyncMock(
            return_value=["ethereum"]
        )

        # Create request data with asset filter
        request_data = ComprehensiveAaveDataRequest(
            networks=["ethereum"],
            asset_symbols=[sample_reserve_data.underlying_token.symbol],
        )

        # Call the router
        result = await get_comprehensive_aave_data(request_data, mock_request)

        # Verify result
        assert isinstance(result, ComprehensiveAaveData)
        # Result may be empty if the filter doesn't match
        for network_data in result.data:
            assert network_data.network == "Ethereum"

    @pytest.mark.asyncio
    async def test_get_comprehensive_aave_data_all_networks(
        self, mock_request, sample_pool_data
    ):
        """Test comprehensive AAVE data retrieval for all networks."""
        # Setup mock client
        mock_request.app.state.aave_client.get_markets_data = AsyncMock(
            return_value=[sample_pool_data]
        )
        mock_request.app.state.aave_client.get_available_networks = AsyncMock(
            return_value=["ethereum", "polygon"]
        )

        # Create request data without network filter
        request_data = ComprehensiveAaveDataRequest(networks=None, asset_symbols=None)

        # Call the router
        result = await get_comprehensive_aave_data(request_data, mock_request)

        # Verify result
        assert isinstance(result, ComprehensiveAaveData)
        # Verify get_available_networks was called
        mock_request.app.state.aave_client.get_available_networks.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_comprehensive_aave_data_api_error(self, mock_request):
        """Test handling of API errors."""
        # Setup mock client to raise error
        mock_request.app.state.aave_client.get_markets_data = AsyncMock(
            side_effect=AaveApiError("API error")
        )
        mock_request.app.state.aave_client.get_available_networks = AsyncMock(
            return_value=["ethereum"]
        )

        # Create request data
        request_data = ComprehensiveAaveDataRequest(
            networks=["ethereum"], asset_symbols=None
        )

        # Call the router and expect error
        with pytest.raises(ToolError, match="AAVE API error"):
            await get_comprehensive_aave_data(request_data, mock_request)

    @pytest.mark.asyncio
    async def test_get_comprehensive_aave_data_client_error(self, mock_request):
        """Test handling of client errors."""
        # Setup mock client to raise error
        mock_request.app.state.aave_client.get_markets_data = AsyncMock(
            side_effect=AaveClientError("Client error")
        )
        mock_request.app.state.aave_client.get_available_networks = AsyncMock(
            return_value=["ethereum"]
        )

        # Create request data
        request_data = ComprehensiveAaveDataRequest(
            networks=["ethereum"], asset_symbols=None
        )

        # Call the router and expect error
        with pytest.raises(ToolError, match="AAVE client error"):
            await get_comprehensive_aave_data(request_data, mock_request)

    @pytest.mark.asyncio
    async def test_get_comprehensive_aave_data_unexpected_error(self, mock_request):
        """Test handling of unexpected errors."""
        # Setup mock client to raise error
        mock_request.app.state.aave_client.get_markets_data = AsyncMock(
            side_effect=ValueError("Unexpected error")
        )
        mock_request.app.state.aave_client.get_available_networks = AsyncMock(
            return_value=["ethereum"]
        )

        # Create request data
        request_data = ComprehensiveAaveDataRequest(
            networks=["ethereum"], asset_symbols=None
        )

        # Call the router and expect error
        with pytest.raises(ToolError, match="An unexpected error occurred"):
            await get_comprehensive_aave_data(request_data, mock_request)
