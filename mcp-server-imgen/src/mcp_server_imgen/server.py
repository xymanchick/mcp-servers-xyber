import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Any

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from pydantic import Field

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

logger = logging.getLogger(__name__)


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
    prompt: Annotated[
        str,
        Field(description="Text prompt describing the desired image", max_length=300),
    ],
    width: Annotated[
        int,
        Field(
            512,
            description="Image width in pixels (128-1024, divisible by 8)",
            ge=128,
            le=1024,
            multiple_of=8,
        ),
    ] = 512,
    height: Annotated[
        int,
        Field(
            512,
            description="Image height in pixels (128-1024, divisible by 8)",
            ge=128,
            le=1024,
            multiple_of=8,
        ),
    ] = 512,
    num_images: Annotated[
        int, Field(1, description="Number of images to generate (1-4)", ge=1, le=4)
    ] = 1,
    seed: Annotated[
        int | None, Field(None, description="Seed for reproducible generation")
    ] = None,
    guidance_scale: Annotated[
        float,
        Field(7.5, description="Prompt guidance scale (1.0-20.0)", ge=1.0, le=20.0),
    ] = 7.5,
    num_inference_steps: Annotated[
        int, Field(50, description="Number of denoising steps (10-100)", ge=10, le=100)
    ] = 50,
) -> str:
    """Generate images from text using Google Vertex AI Stable Diffusion."""
    image_generator = ctx.request_context.lifespan_context["image_generator"]

    try:
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

    except (GoogleServiceError, ImageGenerationServiceError) as service_err:
        logger.error(f"Service error during image generation: {service_err}")
        raise ToolError(
            f"Image generation service error: {service_err}"
        ) from service_err

    except Exception as e:
        logger.error(f"Unexpected error during image generation: {e}", exc_info=True)
        raise ToolError("An unexpected error occurred during image generation.") from e
