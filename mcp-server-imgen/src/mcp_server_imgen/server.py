import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError

from mcp_server_imgen.google_client import (
    GoogleConfigError,
    GoogleServiceError,
    _GoogleService,
    get_gemini_model,
    get_google_service,
)
from mcp_server_imgen.utils import (
    ImageGenerationServiceError,
    _ImageGenerationService,
    get_image_generation_service,
)
from mcp_server_imgen.schemas import GenerateImageRequest

logger = logging.getLogger(__name__)

# --- Lifespan Management --- #
@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[dict[str, Any]]:
    """Manage the lifespan of the image generation service."""
    logger.info("Lifespan: Initializing services...")

    try:
        # Initialize services
        gemini_model = get_gemini_model()
        google_service: _GoogleService = get_google_service()
        image_generator: _ImageGenerationService = get_image_generation_service(
            google_service
        )

        logger.info("Lifespan: Services initialized successfully")
        yield {"image_generator": image_generator, "gemini_model": gemini_model}

    except (GoogleServiceError, GoogleConfigError) as init_err:
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
    request: GenerateImageRequest,
) -> str:
    """Generate images from text using Google Vertex AI Stable Diffusion."""
    image_generator = ctx.request_context.lifespan_context["image_generator"]
    gemini_model = ctx.request_context.lifespan_context["gemini_model"]

    try:
        # Generate images using the validated request data
        image_base64_list = await image_generator.generate_images(
            prompt=request.prompt,
            width=request.width,
            height=request.height,
            num_images=request.num_images,
            seed=request.seed,
            guidance_scale=request.guidance_scale,
            num_inference_steps=request.num_inference_steps,
        )

        logger.info(f"Successfully generated image for prompt: '{request.prompt}'")
        return image_base64_list[0]

    except (GoogleServiceError, ImageGenerationServiceError) as service_err:
        logger.error(f"Service error during image generation: {service_err}")
        raise ToolError(
            f"Image generation service error: {service_err}"
        ) from service_err

    except Exception as e:
        logger.error(
            f"Unexpected error during image generation: {e}", exc_info=True
        )
        raise ToolError(
            "An unexpected error occurred during image generation."
        ) from e
