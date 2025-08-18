import logging
from functools import lru_cache

from mcp_server_imgen.google_client import GoogleServiceError, _GoogleService

logger = logging.getLogger(__name__)


# --- Image Generation Service ---
class ImageGenerationServiceError(Exception):
    """Base exception for errors related to image generation service."""

    pass


class ImageDecodeError(ImageGenerationServiceError):
    """Errors during base64 decoding of image data."""

    pass


class _ImageGenerationService:
    """Handles image generation logic using GoogleService."""

    def __init__(self, google_service: _GoogleService) -> None:
        logger.info("Initializing ImageGenerationService.")
        self.google_service = google_service

    async def generate_images(
        self,
        prompt: str,
        width: int = 512,
        height: int = 512,
        num_images: int = 1,
        seed: int | None = None,
        guidance_scale: float = 3,
        num_inference_steps: int = 50,
    ) -> list[str]:
        """Generate images using Google Vertex AI.

        Raises:
            GoogleAPIError: If the API call fails.
            ImageDecodeError: If the returned image data cannot be decoded.
        """
        logger.info(f"Generating {num_images} image(s) for prompt: '{prompt}'")

        instance = {"prompt": prompt}

        parameters = {
            "height": height,
            "width": width,
            "numInferenceSteps": num_inference_steps,
            "guidanceScale": guidance_scale,
            "num_samples": num_images,
        }
        if seed is not None:
            parameters["seed"] = seed

        try:
            response_data = await self.google_service.predict([instance], parameters)
            image_base64_list = list(response_data.values())

            logger.info(f"Successfully generated {len(image_base64_list)} image(s).")
            return image_base64_list

        except GoogleServiceError as e:
            logger.error(f"Google service error: {e}")
            raise ImageGenerationServiceError(f"Google service error: {e}") from e

        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise ImageGenerationServiceError(f"Unexpected error: {e}") from e


@lru_cache(maxsize=1)
def get_image_generation_service(
    google_service: _GoogleService,
) -> _ImageGenerationService:
    """Get an instance of ImageGenerationService."""
    return _ImageGenerationService(google_service)
