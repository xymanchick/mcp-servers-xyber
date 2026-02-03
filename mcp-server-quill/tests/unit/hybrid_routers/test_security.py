from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

# Sample responses
SAMPLE_SEARCH_RESPONSE = {
    "address": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
    "name": "Wrapped Ether",
    "symbol": "WETH",
    "chainId": "ethereum"
}

SAMPLE_EVM_QUILL_RESPONSE = {
    "tokenInformation": {"tokenName": "WETH"},
    "tokenScore": {"totalScore": {"percent": 90}}
}

SAMPLE_SOLANA_SEARCH_RESPONSE = {
    "address": "4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R",
    "name": "Raydium",
    "symbol": "RAY",
    "chainId": "solana"
}

SAMPLE_SOLANA_QUILL_RESPONSE = {
    "tokenInformation": {"generalInformation": {"tokenName": "Raydium"}},
    "honeypotDetails": {"overAllScorePercentage": 88}
}


@pytest.mark.asyncio
async def test_get_evm_token_info_success(client: AsyncClient) -> None:
    with patch("mcp_server_quill.quill.search.TokenSearchAPI.search_token", new_callable=AsyncMock) as mock_search, \
         patch("mcp_server_quill.quill.client.QuillAPI.get_token_info", new_callable=AsyncMock) as mock_quill:
        
        mock_search.return_value = SAMPLE_SEARCH_RESPONSE
        mock_quill.return_value = SAMPLE_EVM_QUILL_RESPONSE
        
        response = await client.get("/hybrid/evm/WETH")
        
        assert response.status_code == 200
        payload = response.json()
        assert payload["search_result"]["symbol"] == "WETH"
        assert payload["quill_data"]["tokenScore"]["totalScore"]["percent"] == 90
        
        mock_search.assert_called_once()
        mock_quill.assert_called_once()


@pytest.mark.asyncio
async def test_get_evm_token_info_search_failed(client: AsyncClient) -> None:
    with patch("mcp_server_quill.quill.search.TokenSearchAPI.search_token", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = None
        
        response = await client.get("/hybrid/evm/INVALID")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_solana_token_info_success(client: AsyncClient) -> None:
    with patch("mcp_server_quill.quill.search.TokenSearchAPI.search_token", new_callable=AsyncMock) as mock_search, \
         patch("mcp_server_quill.quill.client.QuillAPI.get_solana_token_info", new_callable=AsyncMock) as mock_quill:
        
        mock_search.return_value = SAMPLE_SOLANA_SEARCH_RESPONSE
        mock_quill.return_value = SAMPLE_SOLANA_QUILL_RESPONSE
        
        response = await client.get("/hybrid/solana/RAY")
        
        assert response.status_code == 200
        payload = response.json()
        assert payload["search_result"]["symbol"] == "RAY"
        assert payload["quill_data"]["honeypotDetails"]["overAllScorePercentage"] == 88
        
        mock_search.assert_called_once()
        mock_quill.assert_called_once()
