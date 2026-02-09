from typing import Any

from pydantic import BaseModel, Field


class GenerateCartesiaTTSRequest(BaseModel):
    """Input schema for the generate_cartesia_tts tool."""

    text: str = Field(..., description="The text content to synthesize into speech")
    voice: dict[str, Any] | None = Field(
        default=None,
        description="Optional Cartesia voice configuration to override the default",
    )
    model_id: str | None = Field(
        default=None, description="Optional Cartesia model ID to override the default"
    )
