from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any
from pydantic import ValidationError as PydanticValidationError


from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from mcp_server_cartesia.cartesia_client import (
    CartesiaApiError,
    CartesiaClientError,
    CartesiaConfigError,
    _CartesiaService,
    get_cartesia_service,
)
from mcp_server_cartesia.schemas import GenerateCartesiaTTSRequest

logger = logging.getLogger(__name__)


# --- Custom Exceptions --- #
class ValidationError(ToolError):
    """Custom exception for input validation failures."""

    def __init__(self, message: str, code: str = "VALIDATION_ERROR"):
        self.message = message
        self.code = code
        self.status_code = 400
        super().__init__(message)

# --- Input Schema Definition --- #
# (Schema definitions moved to schemas.py)




# --- Lifespan Management --- #
@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[dict[str, Any]]:
    """Manage server startup/shutdown. Initializes the Cartesia service."""
    logger.info("Lifespan: Initializing services...")

    try:
        # Initialize services
        cartesia_service: _CartesiaService = get_cartesia_service()

        logger.info("Lifespan: Services initialized successfully")
        yield {"cartesia_service": cartesia_service}

    except (CartesiaConfigError, CartesiaClientError) as init_err:
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
mcp_server = FastMCP(
    name="cartesia",
    description="Generate speech from text using Cartesia TTS",
    lifespan=app_lifespan,
)


# --- Tool Definitions --- #
@mcp_server.tool()
async def generate_cartesia_tts(
    ctx: Context,
    request: GenerateCartesiaTTSRequest,
) -> str:
    """Generates speech from the provided text using Cartesia TTS and saves it as a WAV file. Returns the path to the saved file."""
    cartesia_service = ctx.request_context.lifespan_context["cartesia_service"]

    try:
        
        # Log the input parameters
        logger.info(f"Received request to generate speech for text='{request.text[:50]}...'")
        
        # Extract voice ID from voice dictionary if present
        voice_id = request.voice.get("id") if request.voice and "id" in request.voice else None
        logger.info(
            f"Generating speech for text='{request.text[:50]}...', voice='{voice_id or 'default'}', model='{request.model_id or 'default'}'"
        )

        # Execute core logic
        file_path = await cartesia_service.generate_speech(
            text=request.text, voice_id=voice_id, model_id=request.model_id
        )

        logger.info(f"Successfully generated speech and saved to: {file_path}")
        return f"Successfully generated speech and saved to: {file_path}"

    except ValueError as val_err:
        logger.warning(f"Input validation error: {val_err}")
        raise ToolError(f"Input validation error: {val_err}") from val_err
    
    except PydanticValidationError as ve:
        error_details = "\n".join(
            f"  - {'.'.join(str(loc).capitalize() for loc in err['loc'])}: {err['msg']}"
            for err in ve.errors()
        )
        raise ValidationError(f"Invalid parameters:\n{error_details}")

    except (CartesiaClientError, CartesiaApiError, CartesiaConfigError) as cartesia_err:
        logger.error(f"Cartesia service error: {cartesia_err}", exc_info=True)
        raise ToolError(f"Cartesia service error: {cartesia_err}") from cartesia_err

    except IOError as io_err:
        logger.error(f"File system error saving audio: {io_err}", exc_info=True)
        raise ToolError(f"File system error saving audio: {io_err}") from io_err

    except Exception as e:
        logger.error(f"Unexpected error during speech generation: {e}", exc_info=True)
        raise ToolError("An unexpected error occurred during speech generation.") from e
