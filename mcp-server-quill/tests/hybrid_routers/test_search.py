from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

# Sample search response
SAMPLE_SEARCH_RESPONSE = {
    "address": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
    "name": "Wrapped Ether",
    "symbol": "WETH",
    "chainId": "ethereum"
}


@pytest.mark.asyncio
async def test_search_token_address_success(client: AsyncClient) -> None:
    # Mock the search_token method
    with patch("mcp_server_quill.quill.search.TokenSearchAPI.search_token", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = SAMPLE_SEARCH_RESPONSE
        
        response = await client.get("/hybrid/search/WETH")
        
        assert response.status_code == 200
        payload = response.json()
        assert payload["symbol"] == "WETH"
        assert payload["address"] == "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
        mock_search.assert_called_once()


@pytest.mark.asyncio
async def test_search_token_address_with_chain(client: AsyncClient) -> None:
    with patch("mcp_server_quill.quill.search.TokenSearchAPI.search_token", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = SAMPLE_SEARCH_RESPONSE
        
        response = await client.get("/hybrid/search/WETH", params={"chain": "ethereum"})
        
        assert response.status_code == 200
        mock_search.assert_called_with("WETH", chain_id="ethereum")


@pytest.mark.asyncio
async def test_search_token_not_found(client: AsyncClient) -> None:
    with patch("mcp_server_quill.quill.search.TokenSearchAPI.search_token", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = None
        
        response = await client.get("/hybrid/search/INVALID_TOKEN")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
