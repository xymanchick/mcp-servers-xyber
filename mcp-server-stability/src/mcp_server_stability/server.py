import base64
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from pydantic import ValidationError as PydanticValidationError
from mcp_server_stability.schemas import ImageGenerationRequest

from mcp_server_stability.stable_diffusion import (
    StabilityService,
    StableDiffusionClientError,
    StableDiffusionServerConnectionError,
    get_stability_service,
)

logger = logging.getLogger(__name__)

# --- Custom Exceptions --- #
class ValidationError(ToolError):
    """Custom exception for input validation failures."""

    def __init__(self, message: str, code: str = "VALIDATION_ERROR"):
        self.message = message
        self.code = code
        self.status_code = 400
        super().__init__(message)

# --- Lifespan Management for MCP Server --- #


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[dict[str, object]]:
    logger.info("Lifespan: Initializing Stable Diffusion service...")
    stability_service = None
    try:
        stability_service = await get_stability_service()
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
        if stability_service is not None:
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
    prompt: str,
    negative_prompt: str | None = "ugly, inconsistent",
    aspect_ratio: str = "1:1",
    seed: int | None = 42,
    style_preset: str | None = None,
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
        
        # Validate input parameters
        ImageGenerationRequest(
            prompt=prompt,
            negative_prompt=negative_prompt,
            aspect_ratio=aspect_ratio,
            seed=seed,
            style_preset=style_preset,
        )
        
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
    except PydanticValidationError as ve:
        error_details = "; ".join(
            f"{err['loc'][0]}: {err['msg']}" for err in ve.errors()
        )
        logger.warning(f"Validation error: {error_details}")
        raise ValidationError(f"Validation error: {error_details}") from ve
    except Exception as exc:
        logger.error(f"Unexpected error: {exc}", exc_info=True)
        raise ToolError(f"Unexpected error: {exc}") from exc
