import base64
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Literal

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from pydantic import Field

from mcp_server_stability.stable_diffusion import (
    StabilityService,
    StableDiffusionClientError,
    StableDiffusionServerConnectionError,
    get_stability_service,
)

logger = logging.getLogger(__name__)


# --- Lifespan Management for MCP Server --- #


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[dict[str, object]]:
    logger.info("Lifespan: Initializing Stable Diffusion service...")
    try:
        stability_service: StabilityService = await get_stability_service()
        logger.info("Lifespan: Stable Diffusion service initialized successfully.")
        yield {"stability_service": stability_service}

    except StableDiffusionClientError as init_err:
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
        logger.info("Lifespan: Cleaning up Stable Diffusion service.")
        await stability_service.cleanup()
        logger.info(
            "Lifespan: Stable Diffusion service cleanup completed successfully."
        )


# --- MCP Server Initialization --- #

mcp_server = FastMCP("stability-server", lifespan=app_lifespan)

# --- Tool Definitions --- #


@mcp_server.tool()
async def generate_image(
    ctx: Context,
    prompt: Annotated[
        str, Field(description="Text description of the image to generate")
    ],
    negative_prompt: Annotated[
        str | None,
        Field(
            default="ugly, inconsistent",
            max_length=10000,
            description="Text describing what you do not wish to see in the output image",
        ),
    ] = "ugly, inconsistent",
    aspect_ratio: Annotated[
        str,
        Field(
            default="1:1",
            pattern="^(16:9|1:1|21:9|2:3|3:2|4:5|5:4|9:16|9:21)$",
            description="Controls the aspect ratio of the generated image. Common values: '1:1', '16:9', '9:16', '2:3', '3:2'.",
        ),
    ] = "1:1",
    seed: Annotated[
        int | None,
        Field(
            default=42,
            ge=0,
            description="Seed for reproducible generation. Set to 0 for a random seed.",
        ),
    ] = 42,
    style_preset: Annotated[
        Literal[
            "3d-model",
            "analog-film",
            "anime",
            "cinematic",
            "comic-book",
            "digital-art",
            "enhance",
            "fantasy-art",
            "isometric",
            "line-art",
            "low-poly",
            "modeling-compound",
            "neon-punk",
            "origami",
            "photographic",
            "pixel-art",
            "tile-texture",
        ]
        | None,
        Field(
            default=None,
            description="Predefined style preset to guide the image generation. E.g., 'photographic', 'anime'.",
        ),
    ] = None,
) -> str:
    """Generate an image from a prompt using Stable Diffusion and returns it as a base64 encoded string"""
    stability_service: StabilityService = ctx.request_context.lifespan_context[
        "stability_service"
    ]
    params = {
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "aspect_ratio": aspect_ratio,
        "seed": seed,
    }
    if style_preset:
        params["style_preset"] = style_preset

    try:
        response = await stability_service.send_generation_request(params)
        finish_reason = response.headers.get("finish-reason")
        if finish_reason == "CONTENT_FILTERED":
            raise ToolError("Generation failed: NSFW content filtered")

        # Convert the image to a base64 encoded string
        image_data = response.content
        base64_image = base64.b64encode(image_data).decode("utf-8")
        return base64_image

    except (StableDiffusionServerConnectionError, StableDiffusionClientError) as exc:
        logger.error(f"Stable Diffusion error: {exc}")
        raise ToolError(str(exc)) from exc
    except Exception as exc:
        logger.error(f"Unexpected error: {exc}", exc_info=True)
        raise ToolError(f"Unexpected error: {exc}") from exc
