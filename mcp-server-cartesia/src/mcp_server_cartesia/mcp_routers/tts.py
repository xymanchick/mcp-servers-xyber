"""
MCP-only router for Cartesia text-to-speech generation.

Main responsibility: Provide the generate_cartesia_tts tool for AI agents.
"""

import logging

from fastapi import APIRouter, Depends
from mcp_server_cartesia.cartesia_client import (CartesiaApiError,
                                                 CartesiaClientError,
                                                 CartesiaConfigError,
                                                 _CartesiaService)
from mcp_server_cartesia.dependencies import get_cartesia_service
from mcp_server_cartesia.schemas import GenerateCartesiaTTSRequest
from pydantic import ValidationError as PydanticValidationError

logger = logging.getLogger(__name__)
router = APIRouter()


class ValidationError(Exception):
    """Custom exception for input validation failures."""

    def __init__(self, message: str, code: str = "VALIDATION_ERROR"):
        self.message = message
        self.code = code
        self.status_code = 400
        super().__init__(message)


@router.post(
    "/generate-tts",
    tags=["Cartesia"],
    operation_id="generate_cartesia_tts",
)
async def generate_cartesia_tts(
    request: GenerateCartesiaTTSRequest,
    cartesia_service: _CartesiaService = Depends(get_cartesia_service),
) -> dict[str, str]:
    """
    Generates speech from the provided text using Cartesia TTS and saves it as a WAV file.

    This tool is designed for AI agents that need to convert text into speech
    using the Cartesia text-to-speech API. The audio is saved locally and the
    file path is returned.

    Args:
        request: The TTS generation request containing text and optional voice/model parameters
        cartesia_service: The Cartesia service instance (injected)

    Returns:
        A dictionary with a success message and the file path

    Raises:
        ValidationError: If input validation fails
        ValueError: If the text is empty
        CartesiaClientError: For client-side errors
        CartesiaApiError: For API-side errors
        CartesiaConfigError: For configuration errors
        IOError: If file writing fails
    """
    try:
        # Log the input parameters
        logger.info(
            f"Received request to generate speech for text='{request.text[:50]}...'"
        )

        # Extract voice ID from voice dictionary if present
        voice_id = (
            request.voice.get("id") if request.voice and "id" in request.voice else None
        )
        logger.info(
            f"Generating speech for text='{request.text[:50]}...', voice='{voice_id or 'default'}', model='{request.model_id or 'default'}'"
        )

        # Execute core logic
        file_path = await cartesia_service.generate_speech(
            text=request.text, voice_id=voice_id, model_id=request.model_id
        )

        logger.info(f"Successfully generated speech and saved to: {file_path}")
        return {
            "message": f"Successfully generated speech and saved to: {file_path}",
            "file_path": file_path,
        }

    except ValueError as val_err:
        logger.warning(f"Input validation error: {val_err}")
        raise ValidationError(f"Input validation error: {val_err}") from val_err

    except PydanticValidationError as ve:
        error_details = "\n".join(
            f"  - {'.'.join(str(loc).capitalize() for loc in err['loc'])}: {err['msg']}"
            for err in ve.errors()
        )
        raise ValidationError(f"Invalid parameters:\n{error_details}")

    except (CartesiaClientError, CartesiaApiError, CartesiaConfigError) as cartesia_err:
        logger.error(f"Cartesia service error: {cartesia_err}", exc_info=True)
        raise

    except IOError as io_err:
        logger.error(f"File system error saving audio: {io_err}", exc_info=True)
        raise

    except Exception as e:
        logger.error(f"Unexpected error during speech generation: {e}", exc_info=True)
        raise Exception("An unexpected error occurred during speech generation.") from e
