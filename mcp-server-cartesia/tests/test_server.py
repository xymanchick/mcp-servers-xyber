import pytest
import logging
from unittest.mock import AsyncMock
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from typing import Any

from fastmcp import Context
from fastmcp.exceptions import ToolError

from mcp_server_cartesia.cartesia_client import (
    CartesiaApiError,
    CartesiaClientError,
    CartesiaConfigError,
)

logger = logging.getLogger(__name__)


#Helper Functions

async def generate_cartesia_tts_helper(
    ctx: Context,
    text: str,
    voice: dict | None = None,
    model_id: str | None = None,
) -> str:
    cartesia_service = ctx.request_context.lifespan_context["cartesia_service"]

    try:
        voice_id = voice.get("id") if voice and "id" in voice else None
        logger.info(
            f"Generating speech for text='{text[:50]}...', voice='{voice_id or 'default'}', model='{model_id or 'default'}'"
        )

        file_path = await cartesia_service.generate_speech(
            text=text, voice_id=voice_id, model_id=model_id
        )

        logger.info(f"Successfully generated speech and saved to: {file_path}")
        return f"Successfully generated speech and saved to: {file_path}"

    except ValueError as val_err:
        logger.warning(f"Input validation error: {val_err}")
        raise ToolError(f"Input validation error: {val_err}") from val_err

    except (CartesiaClientError, CartesiaApiError, CartesiaConfigError) as cartesia_err:
        logger.error(f"Cartesia service error: {cartesia_err}", exc_info=True)
        raise ToolError(f"Cartesia service error: {cartesia_err}") from cartesia_err

    except IOError as io_err:
        logger.error(f"File system error saving audio: {io_err}", exc_info=True)
        raise ToolError(f"File system error saving audio: {io_err}") from io_err

    except Exception as e:
        logger.error(f"Unexpected error during speech generation: {e}", exc_info=True)
        raise ToolError("An unexpected error occurred during speech generation.") from e


@asynccontextmanager
async def app_lifespan_helper(server) -> AsyncIterator[dict[str, Any]]:
    """Helper function that mimics the app lifespan logic for testing."""
    logger.info("Lifespan: Initializing services...")

    try:
        from mcp_server_cartesia.cartesia_client import get_cartesia_service
        cartesia_service = get_cartesia_service()

        logger.info("Lifespan: Services initialized successfully")
        yield {"cartesia_service": cartesia_service}

    except Exception as init_err:
        logger.error(f"FATAL: Lifespan initialization failed: {init_err}", exc_info=True)
        raise init_err

    finally:
        logger.info("Lifespan: Shutdown cleanup completed")


#TTS Function Tests

@pytest.mark.asyncio
async def test_generate_cartesia_tts_success(mock_context, sample_text, sample_voice_with_id, sample_model_id):
    result = await generate_cartesia_tts_helper(mock_context, text=sample_text, voice=sample_voice_with_id, model_id=sample_model_id)
    assert "Successfully generated speech" in result


@pytest.mark.asyncio
async def test_generate_cartesia_tts_value_error(mock_context):
    mock_context.request_context.lifespan_context["cartesia_service"].generate_speech.side_effect = ValueError("Invalid input")
    with pytest.raises(ToolError) as exc:
        await generate_cartesia_tts_helper(mock_context, text="", voice=None)
    assert "Input validation error" in str(exc.value)


@pytest.mark.asyncio
async def test_generate_cartesia_tts_cartesia_client_error(mock_context):
    mock_context.request_context.lifespan_context["cartesia_service"].generate_speech.side_effect = CartesiaClientError("Service error")
    with pytest.raises(ToolError) as exc:
        await generate_cartesia_tts_helper(mock_context, text="Test", voice=None)
    assert "Cartesia service error" in str(exc.value)


@pytest.mark.asyncio
async def test_generate_cartesia_tts_io_error(mock_context):
    mock_context.request_context.lifespan_context["cartesia_service"].generate_speech.side_effect = IOError("Disk full")
    with pytest.raises(ToolError) as exc:
        await generate_cartesia_tts_helper(mock_context, text="Test", voice=None)
    assert "File system error saving audio" in str(exc.value)


@pytest.mark.asyncio
async def test_generate_cartesia_tts_unexpected_error(mock_context):
    mock_context.request_context.lifespan_context["cartesia_service"].generate_speech.side_effect = RuntimeError("Unknown")
    with pytest.raises(ToolError) as exc:
        await generate_cartesia_tts_helper(mock_context, text="Test", voice=None)
    assert "unexpected error" in str(exc.value).lower()


@pytest.mark.asyncio
async def test_generate_cartesia_tts_with_defaults(mock_context, sample_text):
    result = await generate_cartesia_tts_helper(mock_context, text=sample_text)
    assert "Successfully generated speech" in result
    mock_context.request_context.lifespan_context["cartesia_service"].generate_speech.assert_called_once_with(
        text=sample_text, voice_id=None, model_id=None
    )


@pytest.mark.asyncio
async def test_generate_cartesia_tts_voice_without_id(mock_context, sample_text, sample_voice_without_id):
    result = await generate_cartesia_tts_helper(mock_context, text=sample_text, voice=sample_voice_without_id)
    assert "Successfully generated speech" in result
    mock_context.request_context.lifespan_context["cartesia_service"].generate_speech.assert_called_once_with(
        text=sample_text, voice_id=None, model_id=None
    )


@pytest.mark.asyncio
async def test_generate_cartesia_tts_api_error(mock_context):
    mock_context.request_context.lifespan_context["cartesia_service"].generate_speech.side_effect = CartesiaApiError("API error")
    with pytest.raises(ToolError) as exc:
        await generate_cartesia_tts_helper(mock_context, text="Test", voice=None)
    assert "Cartesia service error" in str(exc.value)


@pytest.mark.asyncio
async def test_generate_cartesia_tts_config_error(mock_context):
    mock_context.request_context.lifespan_context["cartesia_service"].generate_speech.side_effect = CartesiaConfigError("Config error")
    with pytest.raises(ToolError) as exc:
        await generate_cartesia_tts_helper(mock_context, text="Test", voice=None)
    assert "Cartesia service error" in str(exc.value)


#Lifespan Management Tests

@pytest.mark.asyncio
async def test_app_lifespan_init_success(monkeypatch):
    fake_service = AsyncMock()
    monkeypatch.setattr("mcp_server_cartesia.cartesia_client.get_cartesia_service", lambda: fake_service)
    
    class DummyServer: 
        pass
    
    async with app_lifespan_helper(DummyServer()) as ctx:
        assert "cartesia_service" in ctx
        assert ctx["cartesia_service"] == fake_service


@pytest.mark.asyncio
async def test_app_lifespan_cartesia_config_error(monkeypatch):
    def mock_get_service():
        raise CartesiaConfigError("Invalid configuration")
    
    monkeypatch.setattr("mcp_server_cartesia.cartesia_client.get_cartesia_service", mock_get_service)
    
    class DummyServer: 
        pass
    
    with pytest.raises(CartesiaConfigError):
        async with app_lifespan_helper(DummyServer()):
            pass


@pytest.mark.asyncio
async def test_app_lifespan_cartesia_client_error(monkeypatch):
    def mock_get_service():
        raise CartesiaClientError("Client initialization failed")
    
    monkeypatch.setattr("mcp_server_cartesia.cartesia_client.get_cartesia_service", mock_get_service)
    
    class DummyServer: 
        pass
    
    with pytest.raises(CartesiaClientError):
        async with app_lifespan_helper(DummyServer()):
            pass


@pytest.mark.asyncio
async def test_app_lifespan_unexpected_error(monkeypatch):
    def mock_get_service():
        raise RuntimeError("Unexpected error")
    
    monkeypatch.setattr("mcp_server_cartesia.cartesia_client.get_cartesia_service", mock_get_service)
    
    class DummyServer: 
        pass
    
    with pytest.raises(RuntimeError):
        async with app_lifespan_helper(DummyServer()):
            pass
