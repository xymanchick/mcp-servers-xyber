from __future__ import annotations

from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from mcp_server_quill.quill.search import TokenSearchAPI


@pytest.mark.asyncio
async def test_search_token_known_tokens() -> None:
    search_api = TokenSearchAPI()
    
    # The issue is likely that AsyncClient context manager return value is not being handled correctly
    # or that the mocked client instance methods are not async.
    
    # Let's mock the class itself to return a specific instance
    mock_client_instance = MagicMock()
    mock_client_instance.__aenter__.return_value = mock_client_instance
    mock_client_instance.__aexit__.return_value = None
    
    # Important: .get must be an async method (coroutine)
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        "pairs": [{
            "baseToken": {"symbol": "WETH", "name": "Wrapped Ether", "address": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"},
            "chainId": "ethereum",
            "volume": {"h24": 1000000}
        }]
    }
    
    mock_client_instance.get = AsyncMock(return_value=mock_response)
    
    with patch("httpx.AsyncClient", return_value=mock_client_instance):
        result = await search_api.search_token("WETH", chain_id="ethereum")
        
        assert result is not None
        assert result["symbol"] == "WETH"
        assert result["address"] == "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"


@pytest.mark.asyncio
async def test_search_token_api_fallback() -> None:
    search_api = TokenSearchAPI()
    
    mock_client_instance = MagicMock()
    mock_client_instance.__aenter__.return_value = mock_client_instance
    mock_client_instance.__aexit__.return_value = None
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        "pairs": [{
            "baseToken": {"symbol": "PEPE", "name": "Pepe", "address": "0x6982508145454Ce325dDbE47a25d4ec3d2311933"},
            "chainId": "ethereum",
            "volume": {"h24": 500000}
        }]
    }
    
    mock_client_instance.get = AsyncMock(return_value=mock_response)
    
    with patch("httpx.AsyncClient", return_value=mock_client_instance):
        result = await search_api.search_token("PEPE", chain_id="ethereum")
        
        assert result is not None
        assert result["symbol"] == "PEPE"
        assert result["chainId"] == "ethereum"
