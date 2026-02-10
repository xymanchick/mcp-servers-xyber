from __future__ import annotations

import asyncio
import base64
import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from mcp_server_elevenlabs.config import get_app_settings
from mcp_server_elevenlabs.elevenlabs.client import generate_voice
from mcp_server_elevenlabs.schemas import GenerateVoiceResponse, VoiceRequest

router = APIRouter(tags=["TTS"])
logger = logging.getLogger(__name__)


@router.post(
    "/generate-voice",
    response_model=GenerateVoiceResponse,
    operation_id="elevenlabs_generate_voice",
    summary="Generate Voice Audio",
    description=(
        "Generates an MP3 audio file from text using the ElevenLabs API.\n\n"
        "- Always returns a JSON payload (MCP-friendly)\n"
        "- Includes a `download_url` to fetch the audio via REST\n"
        "- Optionally embeds `audio_base64` when `return_audio_base64=true`"
    ),
)
async def generate_voice_endpoint(
    request: VoiceRequest, http_request: Request
) -> GenerateVoiceResponse:
    """Generate voice audio and return a JSON payload (MCP-friendly)."""
    try:
        settings = get_app_settings()

        filename = await asyncio.to_thread(
            generate_voice,
            text=request.text,
            api_config=settings.elevenlabs,
            file_path=str(settings.media.voice_output_dir),
            voice_id=request.voice_id,
            model_id=request.model_id,
        )

        file_path = settings.media.voice_output_dir / filename
        audio_bytes = file_path.stat().st_size

        base_url = str(http_request.base_url).rstrip("/")
        download_url = f"{base_url}/hybrid/audio/{filename}"

        audio_base64: str | None = None
        if request.return_audio_base64:
            if audio_bytes > request.max_audio_bytes:
                raise HTTPException(
                    status_code=413,
                    detail=(
                        f"Generated audio is {audio_bytes} bytes which exceeds "
                        f"max_audio_bytes={request.max_audio_bytes}. "
                        "Fetch it via download_url instead."
                    ),
                )

            audio_data = await asyncio.to_thread(file_path.read_bytes)
            audio_base64 = base64.b64encode(audio_data).decode("utf-8")

        return GenerateVoiceResponse(
            success=True,
            filename=filename,
            media_type="audio/mpeg",
            download_url=download_url,
            audio_bytes=audio_bytes,
            audio_base64=audio_base64,
        )

    except ValueError as e:
        # e.g., missing ELEVENLABS_API_KEY
        raise HTTPException(status_code=400, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        logger.exception("Unexpected error generating audio")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get(
    "/audio/{filename}",
    summary="Download Audio File",
    description="Downloads a generated audio file by filename.",
    response_class=FileResponse,
)
async def download_audio(filename: str):
    """Serve audio files for download."""
    settings = get_app_settings()
    audio_dir = settings.media.voice_output_dir

    # Path traversal protection: ensure resolved path stays within audio_dir.
    base = audio_dir.resolve()
    candidate = (audio_dir / filename).resolve()
    if not candidate.is_relative_to(base):
        raise HTTPException(status_code=400, detail="Invalid filename")
    file_path = candidate

    if not file_path.exists():
        raise HTTPException(
            status_code=404, detail=f"Audio file '{filename}' not found"
        )

    if not file_path.is_file():
        raise HTTPException(status_code=404, detail=f"'{filename}' is not a valid file")

    return FileResponse(path=str(file_path), media_type="audio/mpeg", filename=filename)
