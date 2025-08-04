import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Any

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from pydantic import ValidationError as PydanticValidationError


from mcp_server_imgen.google_client import (
    GoogleServiceError,
    _GoogleService,
    get_google_service,
)
from mcp_server_imgen.utils import (
    ImageGenerationServiceError,
    _ImageGenerationService,
    get_image_generation_service,
)
from mcp_server_imgen.schemas import GenerateImageRequest

logger = logging.getLogger(__name__)

# --- Custom Exceptions --- #
class ValidationError(ToolError):
    """Custom exception for input validation failures."""

    def __init__(self, message: str, code: str = "VALIDATION_ERROR"):
        self.message = message
        self.code = code
        self.status_code = 400
        super().__init__(message)

# --- Lifespan Management --- #
@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[dict[str, Any]]:
    """Manage the lifespan of the image generation service."""
    logger.info("Lifespan: Initializing services...")

    try:
        # Initialize services
        google_service: _GoogleService = get_google_service()
        image_generator: _ImageGenerationService = get_image_generation_service(
            google_service
        )

        logger.info("Lifespan: Services initialized successfully")
        yield {"image_generator": image_generator}

    except GoogleServiceError as init_err:
        logger.error(
            f"FATAL: Lifespan initialization failed: {init_err}", exc_info=True
        )
        raise init_err

    except Exception as startup_err:
        logger.error(
            f"FATAL: Unexpected error during lifespan initialization: {startup_err}",
            exc_info=True,
        )
        raise startup_err

    finally:
        logger.info("Lifespan: Shutdown cleanup completed")


# --- MCP Server Initialization --- #
mcp_server = FastMCP(name="imgen", lifespan=app_lifespan)


# --- Tool Definitions --- #
@mcp_server.tool()
async def generate_image(
    ctx: Context,
    prompt: str,
    width: int,
    height: int,
    num_images: int,
    seed: int,
    guidance_scale: float,
    num_inference_steps: int,
) -> str:
    """Generate images from text using Google Vertex AI Stable Diffusion."""
    image_generator = ctx.request_context.lifespan_context["image_generator"]

    try:
        
        # Validate input parameters
        GenerateImageRequest(
            prompt=prompt,
            width=width,
            height=height,
            num_images=num_images,
            seed=seed,
            guidance_scale=guidance_scale,
            num_inference_steps=num_inference_steps,
        )
        
        # Generate images
        image_base64_list = await image_generator.generate_images(
            prompt=prompt,
            width=width,
            height=height,
            num_images=num_images,
            seed=seed,
            guidance_scale=guidance_scale,
            num_inference_steps=num_inference_steps,
        )

        logger.info(f"Successfully generated image for prompt: '{prompt}'")
        return image_base64_list[0]
    
    except PydanticValidationError as ve:
        logger.warning(f"Validation error: {ve}")
        error_details = "; ".join(
            f"{err['loc'][0]}: {err['msg']}" for err in ve.errors()
        )
        raise ValidationError(f"Invalid parameters: {error_details}")

    except (GoogleServiceError, ImageGenerationServiceError) as service_err:
        logger.error(f"Service error during image generation: {service_err}")
        raise ToolError(
            f"Image generation service error: {service_err}"
        ) from service_err

    except Exception as e:
        logger.error(f"Unexpected error during image generation: {e}", exc_info=True)
        raise ToolError("An unexpected error occurred during image generation.") from e
