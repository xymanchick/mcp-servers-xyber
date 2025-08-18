import logging

import httpx
from mcp_server_stability.stable_diffusion.config import (
    StableDiffusionClientConfig,
    StableDiffusionClientError,
    StableDiffusionServerConnectionError,
)

logger = logging.getLogger(__name__)


class StabilityService:
    def __init__(self, config: StableDiffusionClientConfig):
        self.api_key = config.api_key
        self.host = config.url
        self.client: httpx.AsyncClient | None = None

    async def _initialize_client(self) -> None:
        """
        Lazily initialize the Stability HTTPX client.

        Raises:
            StableDiffusionClientError: If client initialization fails

        """
        if self.client is None:
            logger.info("Initializing Stability HTTPX client.")
            try:
                self.client = httpx.AsyncClient(
                    timeout=httpx.Timeout(connect=5.0, read=60.0, write=10.0, pool=5.0),
                    headers={
                        "Accept": "image/*",
                        "Authorization": f"Bearer {self.api_key}",
                    },
                )
                logger.info("Stability HTTPX client initialized successfully.")
            except Exception as e:
                logger.error(f"Failed to initialize Stability HTTPX client: {e}")
                raise StableDiffusionClientError(
                    f"Failed to initialize Stability HTTPX client: {str(e)}"
                ) from e

    async def cleanup(self) -> None:
        """
        Cleanup resources by closing the client if it exists.
        This should be called when the service is being shut down.
        """
        if self.client is not None:
            logger.info("Cleaning up Stability HTTPX client.")
            await self.client.aclose()
            self.client = None
            logger.info("Stability HTTPX client closed successfully.")

    async def send_generation_request(self, params: dict) -> httpx.Response:
        """
        Send a generation request to the Stability API.

        Args:
            params: Dictionary containing the generation parameters

        Returns:
            httpx.Response: The response from the API

        Raises:
            StableDiffusionServerConnectionError: If there's a connection error
            StableDiffusionClientError: If there's an API error

        """
        await self._initialize_client()

        try:
            response = await self.client.post(
                self.host, files={"none": ""}, data=params
            )

        except httpx.RequestError as exc:
            raise StableDiffusionServerConnectionError(
                f"Error during request: {exc}"
            ) from exc

        if not response.is_success:
            raise StableDiffusionClientError(
                f"API error: {response.status_code} - {response.text}"
            )

        return response


async def get_stability_service() -> StabilityService:
    config = StableDiffusionClientConfig()
    return StabilityService(config)
