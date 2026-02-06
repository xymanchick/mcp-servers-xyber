from __future__ import annotations

import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from mcp_server_elevenlabs.config import get_app_settings
from mcp_server_elevenlabs.elevenlabs.client import generate_voice
from mcp_server_elevenlabs.schemas import VoiceRequest, GenerateVoiceResponse

router = APIRouter(tags=["TTS"])
logger = logging.getLogger(__name__)


async def perform_generate_voice(
    text: str,
    voice_id: str | None = None,
    model_id: str | None = None,
) -> GenerateVoiceResponse:
    settings = get_app_settings()
    try:
        filename = generate_voice(
            text=text,
            api_config=settings.elevenlabs,
            file_path=str(settings.media.voice_output_dir),
            voice_id=voice_id,
            model_id=model_id,
        )
        file_path = settings.media.voice_output_dir / filename
        return GenerateVoiceResponse(
            success=True,
            filename=filename,
            file_path=str(file_path),
            media_type="audio/mpeg",
        )
    except Exception as e:
        logger.error(f"Error generating voice: {e}")
        raise e


@router.post(
    "/generate-voice",
    response_class=FileResponse,
    operation_id="elevenlabs_generate_voice",
    summary="Generate Voice Audio",
    description="Generates an MP3 audio file from text using the ElevenLabs API. Returns the audio file directly.",
)
async def generate_voice_endpoint(request: VoiceRequest):
    """Generate voice audio and return it directly as an MP3 file."""
    try:
        # Note: The original implementation returned the file directly.
        # The hybrid approach usually returns a JSON response for MCP compatibility,
        # but for file downloads, it's tricky.
        # However, `gitparser` returns `ConvertResponse` (JSON).
        # If we want to be "totally in the same way", we should probably return a JSON response
        # containing the file path or content, but the original `elevenlabs` server returned the file.
        # The user said "adapt ... to the mcp format ... totally in the same way as is in @mcp-server-gitparser".
        # `gitparser` returns JSON with `file_path`.
        # I will change the response to be JSON based for the MCP tool consistency,
        # OR I can have the MCP tool return the path, and the REST endpoint return the file.
        # But `gitparser` uses the SAME router for both.
        # `fastmcp` tools typically return text or JSON. Returning a FileResponse object from an MCP tool might not work as expected
        # if the client expects text.
        # Let's look at `gitparser` again. It returns `ConvertResponse` which has `file_path` and `markdown` content.
        # So for `elevenlabs`, I should probably return a JSON response with the path to the file.
        # But the original `elevenlabs` endpoint returned `FileResponse`.
        # I will stick to returning `FileResponse` for the HTTP endpoint if possible, but
        # `fastmcp` uses the return value.
        # If I decorate with `@router.post`, FastAPI handles it.
        # When `FastMCP.from_fastapi` is used, it inspects the route.
        # If the route returns `FileResponse`, FastMCP might not handle it well for an MCP tool call (which expects text/json).
        # Let's check `gitparser`'s `ConvertResponse`. It's a Pydantic model.
        # I will implement `perform_generate_voice` to return `GenerateVoiceResponse` (JSON).
        # But wait, the original `main.py` had `response_class=FileResponse`.
        # If I change it to JSON, I break the "download" aspect of the REST API unless I add a separate download endpoint.
        # `gitparser` has `docs` saved to disk and returns the content + path.
        # I will return `GenerateVoiceResponse` (JSON) which includes the path.
        # And I'll add a separate GET endpoint to download the file (which `gitparser` doesn't explicitly have in `hybrid_routers`, but `elevenlabs` had it).
        
        result = await perform_generate_voice(
            text=request.text,
            voice_id=request.voice_id,
            model_id=request.model_id,
        )
        
        # If we are called via REST and want to return the file, we might need a separate endpoint or flag.
        # But to be "totally in the same way as gitparser", gitparser returns JSON.
        # So I will return JSON.
        # However, to preserve the "FileResponse" behavior for the user's convenience (if they rely on it),
        # I might need to diverge or offer a way to get the file.
        # The user said "adapt ... to the mcp format ... totally in the same way".
        # So I will follow `gitparser` and return JSON.
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
    file_path = audio_dir / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Audio file '{filename}' not found")
    
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail=f"'{filename}' is not a valid file")
    
    return FileResponse(
        path=str(file_path),
        media_type="audio/mpeg",
        filename=filename
    )
