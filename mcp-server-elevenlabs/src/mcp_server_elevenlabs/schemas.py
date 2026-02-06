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


class GenerateVoiceResponse(BaseModel):
    success: bool
    filename: str
    file_path: str
    media_type: str
