from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from mcp_server_elevenlabs.config import get_app_settings
from mcp_server_elevenlabs.elevenlabs.client import generate_voice
from mcp_server_elevenlabs.schemas import VoiceRequest

router = APIRouter(tags=["TTS"])
logger = logging.getLogger(__name__)


@router.post(
    "/generate-voice-file",
    summary="Generate Voice Audio (direct download)",
    description=(
        "Generates an MP3 audio file from text using the ElevenLabs API and returns it "
        "directly as an `audio/mpeg` download (single-step REST flow)."
    ),
    response_class=FileResponse,
)
async def generate_voice_file_endpoint(request: VoiceRequest) -> FileResponse:
    """
    REST-only convenience endpoint.

    This is intentionally API-only (not MCP) because MCP tools should return JSON.
    """
    settings = get_app_settings()
    try:
        filename = await asyncio.to_thread(
            generate_voice,
            text=request.text,
            api_config=settings.elevenlabs,
            file_path=str(settings.media.voice_output_dir),
            voice_id=request.voice_id,
            model_id=request.model_id,
        )
        file_path = settings.media.voice_output_dir / filename
        return FileResponse(
            path=str(file_path),
            media_type="audio/mpeg",
            filename=filename,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:  # noqa: BLE001
        logger.exception("Unexpected error generating audio")
        raise HTTPException(status_code=500, detail="Internal server error") from e
