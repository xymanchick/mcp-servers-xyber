import httpx
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

class QuillAPI:
    def __init__(self, api_key: str, base_url: str = "https://check-api.quillai.network/api/v1"):
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json"
        }

    async def get_token_info(self, token_address: str, chain_id: str = "1") -> Dict[str, Any]:
        """
        Get security information for a specific token (Async).
        
        Args:
            token_address: The contract address of the token.
            chain_id: The network chain ID (default "1" for Ethereum).
        """
        url = f"{self.base_url}/tokens/information/{token_address}"
        params = {"chainId": chain_id}
        
        async with httpx.AsyncClient(headers=self.headers, timeout=30.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()

    async def get_solana_token_info(self, token_address: str) -> Dict[str, Any]:
        """
        Get security information for a Solana token (Async).
        
        Args:
            token_address: The Solana mint address of the token.
        """
        url = f"{self.base_url}/tokens/solana/{token_address}"
        
        async with httpx.AsyncClient(headers=self.headers, timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()
