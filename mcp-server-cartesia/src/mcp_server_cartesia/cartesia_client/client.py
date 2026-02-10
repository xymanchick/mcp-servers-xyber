# src/mcp_server_cartesia/cartesia_client/client.py

import logging
import os
import uuid
from functools import lru_cache

import aiofiles

try:
    from cartesia import AsyncCartesia
except ImportError:
    logging.getLogger(__name__).warning(
        "Cartesia library not found. Cartesia functionality will be unavailable."
    )


# Import local config and error classes
from .config import (
    CartesiaApiError,
    CartesiaClientError,
    CartesiaConfig,
    CartesiaConfigError,
)

logger = logging.getLogger(__name__)


async def generate_voice_async(
    config: CartesiaConfig,
    text: str,
    voice_id: str | None = None,
    model_id: str | None = None,
) -> str:
    """
    Asynchronously generates voice using Cartesia API and saves it as a WAV file.

    Args:
        config: The Cartesia configuration object.
        text: The text content to synthesize.
        voice_id: Specific voice ID to use (overrides config default).
        model_id: Specific model ID to use (overrides config default).

    Returns:
        The absolute path to the saved WAV file as a string on success.

    Raises:
        CartesiaConfigError: If configuration is invalid (e.g., missing API key).
        ValueError: If input text is empty.
        CartesiaApiError: For errors during the Cartesia API call.
        CartesiaClientError: For general client issues (e.g., library not installed, unexpected errors).
        IOError: If writing the output file fails.

    """
    if AsyncCartesia is None:
        # This indicates a setup issue, maybe raise a more specific error or handle it differently
        raise CartesiaClientError(
            "Cartesia library is not installed. Cannot generate voice."
        )

    # --- Configuration Checks ---
    if not config.api_key:
        # This should ideally be caught during service initialization, but double-check
        raise CartesiaConfigError("Cartesia API key is missing in configuration.")
    if not text:
        logger.warning("Empty text provided for voice generation.")
        raise ValueError(
            "Input text cannot be empty for voice generation."
        )  # Raise ValueError for bad input

    # --- Determine Parameters ---
    selected_voice_id = voice_id if voice_id is not None else config.voice_id
    selected_model_id = model_id if model_id is not None else config.model_id
    output_format = config.output_format
    output_dir = config.absolute_output_dir

    # --- Generate Unique Filename ---
    unique_filename = f"cartesia_output_{uuid.uuid4()}.wav"
    output_file_path = os.path.join(output_dir, unique_filename)

    logger.info(
        f"Requesting Cartesia TTS. Model: '{selected_model_id}', Voice: '{selected_voice_id}', Output: '{output_file_path}'"
    )
    logger.debug(f"TTS Request Text Preview: '{text[:100]}...'")

    audio_bytes = None
    try:
        # --- Call Cartesia API ---
        async with AsyncCartesia(api_key=config.api_key) as client:
            # Handle async generator returned by client.tts.bytes()
            audio_generator = client.tts.bytes(
                model_id=selected_model_id,
                transcript=text,
                voice={"id": selected_voice_id},
                output_format=output_format,
                # Consider adding timeout if the library supports it
            )

            # Collect all audio chunks
            audio_chunks = []
            async for chunk in audio_generator:
                audio_chunks.append(chunk)

            # Combine all chunks into a single bytes object
            audio_bytes = b"".join(audio_chunks)

            if not audio_bytes:
                # Should not happen if API call succeeds, but check just in case
                raise CartesiaApiError(
                    "Cartesia API returned no audio data despite successful call."
                )
            logger.info(
                f"Received {len(audio_bytes)} bytes of audio data from Cartesia."
            )

    except TimeoutError as timeout_err:  # Catch potential timeouts if underlying library uses asyncio timeouts
        logger.error(
            f"Timeout error during Cartesia API call: {timeout_err}", exc_info=True
        )
        raise CartesiaApiError(
            "Timeout occurred while contacting Cartesia API."
        ) from timeout_err
    except Exception as e:
        logger.error(f"Unexpected error during Cartesia API call: {e}", exc_info=True)
        # Wrap in a generic client error
        raise CartesiaClientError(
            f"Unexpected error contacting Cartesia API: {e}"
        ) from e

    # --- Save the Audio File Asynchronously ---
    try:
        async with aiofiles.open(output_file_path, "wb") as afp:
            await afp.write(audio_bytes)
        logger.info(f"Audio successfully saved to {output_file_path}")
        return output_file_path  # Return the full path string on success

    except OSError as e:
        logger.error(
            f"Error writing audio data to file {output_file_path}: {e}", exc_info=True
        )
        # Re-raise IOError so the caller (MCP server) knows it's a file system issue
        raise
    except Exception as e:
        # Catch any other unexpected error during file writing
        logger.error(
            f"Unexpected error writing audio file {output_file_path}: {e}",
            exc_info=True,
        )
        raise CartesiaClientError(f"Unexpected error saving audio file: {e}") from e


# --- Service Class (Good Practice) ---
class _CartesiaService:
    """Encapsulates Cartesia client logic and configuration."""

    def __init__(self, config: CartesiaConfig):
        self.config = config
        # Check for library during initialization
        if AsyncCartesia is None:
            logger.error("Cartesia library not installed. Service will be unavailable.")
            # Optionally raise CartesiaClientError here to prevent service creation

    async def generate_speech(
        self,
        text: str,
        voice_id: str | None = None,
        model_id: str | None = None,
    ) -> str:
        """
        Generates speech using the configured Cartesia client.

        Args:
            text: The text content to synthesize.
            voice_id: Specific voice ID to use (overrides config default).
            model_id: Specific model ID to use (overrides config default).

        Returns:
            The absolute path to the saved WAV file on success.

        Raises:
            Various CartesiaClientError, CartesiaApiError, CartesiaConfigError, ValueError, IOError
            as defined in generate_voice_async.

        """
        if AsyncCartesia is None:
            # Ensure service doesn't proceed if library is missing
            raise CartesiaClientError("Cartesia library is not installed.")

        # Delegate to the core generation function, passing the service's config
        return await generate_voice_async(
            config=self.config, text=text, voice_id=voice_id, model_id=model_id
        )


@lru_cache(maxsize=1)
def get_cartesia_service() -> _CartesiaService:
    """
    Factory function to get a singleton instance of the Cartesia service.
    Handles configuration loading and service initialization.

    Returns:
        An initialized _CartesiaService instance.

    Raises:
        CartesiaConfigError: If configuration loading or validation fails.
        CartesiaClientError: If the Cartesia library isn't installed.

    """
    logger.debug("Attempting to get Cartesia service instance...")
    try:
        config = CartesiaConfig()  # Load and validate config from environment/.env
        service = _CartesiaService(config=config)
        # Check again if library was found during service init
        if AsyncCartesia is None:
            raise CartesiaClientError(
                "Cartesia library not installed. Cannot create service."
            )
        logger.info("Cartesia service instance retrieved successfully.")
        return service
    except (CartesiaConfigError, CartesiaClientError) as e:
        # Catch specific errors during config/service init
        logger.error(
            f"FATAL: Failed to initialize Cartesia service: {e}", exc_info=True
        )
        raise  # Re-raise the specific error
    except Exception as e:
        # Catch any other unexpected error during config/service init
        logger.error(
            f"FATAL: Unexpected error initializing Cartesia service: {e}", exc_info=True
        )
        # Wrap in a standard error type
        raise CartesiaConfigError(
            f"Unexpected error during Cartesia service initialization: {e}"
        ) from e
