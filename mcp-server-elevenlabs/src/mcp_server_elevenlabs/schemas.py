from typing import Optional

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    version: str


class VoiceRequest(BaseModel):
    text: str = Field(
        ...,
        description="The text content to convert to speech.",
        examples=["Hello, this is a test."]
    )
    voice_id: Optional[str] = Field(
        None,
        description="The ID of the voice to use. Overrides the default configuration.",
        examples=["21m00Tcm4TlvDq8ikWAM"]
    )
    model_id: Optional[str] = Field(
        None,
        description="""The ID of the model to use. Overrides the default configuration.

Available models: eleven_v3, eleven_ttv_v3, eleven_multilingual_v2, eleven_flash_v2_5, eleven_flash_v2, eleven_turbo_v2_5, eleven_turbo_v2, eleven_multilingual_v1, eleven_english_sts_v2, eleven_english_sts_v1""",
        examples=["eleven_multilingual_v2", "eleven_flash_v2_5", "eleven_v3"]
    )
    return_audio_base64: bool = Field(
        default=False,
        description=(
            "If true, the response will include the generated audio as base64. "
            "This is the most MCP-friendly way to return audio bytes."
        ),
    )
    max_audio_bytes: int = Field(
        default=5_000_000,
        ge=1,
        description=(
            "Maximum allowed audio file size (bytes) when return_audio_base64=true. "
            "Prevents huge MCP payloads."
        ),
    )


class GenerateVoiceResponse(BaseModel):
    success: bool
    filename: str
    file_path: str
    media_type: str
    download_url: str
    audio_bytes: int
    audio_base64: Optional[str] = None