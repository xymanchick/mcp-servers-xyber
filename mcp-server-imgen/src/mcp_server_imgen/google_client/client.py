import asyncio
import logging
from functools import lru_cache
from typing import Any

from google.auth.transport.requests import Request
from google.cloud import aiplatform_v1
from google.oauth2.service_account import Credentials
from google.protobuf import json_format, struct_pb2

from mcp_server_imgen.google_client.config import (
    EmptyPredictionError,
    GoogleAPIError,
    GoogleConfig,
    GoogleConfigError,
)

# --- Google Vertex AI Service Logic --- #

logger = logging.getLogger(__name__)


class _GoogleService:
    """Handles communication with the Google Vertex AI Prediction Service."""

    def __init__(self, config: GoogleConfig) -> None:
        self.config = config
        logger = logging.getLogger(__name__)
        logger.info("Initializing GoogleService.")
        try:
            self._credentials = self._initialize_credentials()
            self._client = self._initialize_client()
            self._endpoint = self._initialize_endpoint()
        except GoogleConfigError:  # Catch config errors during init
            # Logged in init methods, re-raise
            raise
        except Exception as e:
            # Catch unexpected init errors
            logger.error(
                f"Unexpected error during GoogleService init: {e}", exc_info=True
            )
            raise GoogleConfigError(
                f"Unexpected error initializing GoogleService: {e}"
            ) from e

    def _initialize_credentials(self) -> Credentials:
        logger.info("Initializing Google credentials.")
        try:
            credentials = Credentials.from_service_account_info(
                self.config.credentials_info
            )
            logger.info("Google credentials initialized successfully.")
            return credentials
        except FileNotFoundError as e:
            raise GoogleConfigError(
                f"Credentials file not found at {self.config.credentials_path}"
            ) from e
        except Exception as e:
            logger.error(f"Failed to initialize Google credentials: {e}", exc_info=True)
            raise GoogleConfigError(
                f"Failed to initialize Google credentials: {e}"
            ) from e

    def _initialize_client(self) -> aiplatform_v1.PredictionServiceAsyncClient:
        logger.info("Initializing Google PredictionServiceAsyncClient.")
        try:
            client = aiplatform_v1.services.prediction_service.async_client.PredictionServiceAsyncClient(
                credentials=self._credentials,
                client_options={"api_endpoint": self.config.api_endpoint},
            )
            logger.info("Google PredictionServiceAsyncClient initialized successfully.")
            return client
        except Exception as e:
            logger.error(
                f"Failed to initialize Google PredictionServiceAsyncClient: {e}",
                exc_info=True,
            )
            raise GoogleConfigError(
                f"Failed to initialize Google PredictionServiceAsyncClient: {e}"
            ) from e

    def _initialize_endpoint(self) -> str:
        logger.info("Initializing Google endpoint path.")
        try:
            endpoint: str = self._client.endpoint_path(
                project=self.config.project_id,
                location=self.config.location,
                endpoint=self.config.endpoint_id,
            )
            logger.info("Google endpoint path initialized successfully.")
            return endpoint
        except Exception as e:
            logger.error(
                f"Failed to initialize Google endpoint path: {e}", exc_info=True
            )
            raise GoogleConfigError(
                f"Failed to initialize Google endpoint path: {e}"
            ) from e

    async def _refresh_credentials(self) -> bool:
        if hasattr(self, "_credentials") and self._credentials.expired:
            logger.info("Refreshing Google credentials.")
            try:
                await asyncio.to_thread(self._credentials.refresh, Request())
                logger.info("Google credentials refreshed successfully.")
                return True
            except Exception as e:
                logger.error(f"Failed to refresh credentials: {e}", exc_info=True)
                return False
        return True

    async def predict(
        self, instances: list[dict[str, Any]], parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Sends prediction request, returns parsed JSON dict response."""
        if not await self._refresh_credentials():
            raise GoogleAPIError("Failed to refresh Google credentials")

        if not instances:
            raise GoogleAPIError("Prediction requires at least one instance")

        try:
            proto_instances = [
                json_format.ParseDict(inst, struct_pb2.Value()) for inst in instances
            ]
            params_proto = json_format.ParseDict(parameters, struct_pb2.Value())

            logger.debug(f"Sending prediction request to endpoint: {self._endpoint}")

            response = await self._client.predict(
                endpoint=self._endpoint,
                instances=proto_instances,
                parameters=params_proto,
                timeout=200.0,
            )

            if not response.predictions:
                raise EmptyPredictionError("API endpoint returned empty prediction")

            result_dict = {}
            for instance, prediction in zip(
                instances, response.predictions, strict=False
            ):
                result_dict[instance["prompt"]] = prediction

            logger.debug("Prediction request successful.")

            return result_dict

        except EmptyPredictionError as exc:
            error_msg = "API endpoint returned empty prediction"
            logger.error(error_msg, exc_info=True)
            raise EmptyPredictionError(error_msg) from exc

        except Exception as exc:
            error_msg = f"Prediction API call failed: {exc}"
            logger.error(error_msg, exc_info=True)
            raise GoogleAPIError(error_msg) from exc


@lru_cache(maxsize=1)
def get_google_service() -> _GoogleService:
    """Get an instance of GoogleService."""
    config = GoogleConfig()
    return _GoogleService(config)
