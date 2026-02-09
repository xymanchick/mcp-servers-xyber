from typing import Literal

from pydantic import BaseModel, Field


class ImageGenerationRequest(BaseModel):
    """Input schema for an image generation tool with style and aspect ratio options."""

    prompt: str = Field(..., description="Text description of the image to generate")

    negative_prompt: str | None = Field(
        default="ugly, inconsistent",
        max_length=10000,
        description="Text describing what you do not wish to see in the output image",
    )

    aspect_ratio: str = Field(
        default="1:1",
        pattern=r"^(16:9|1:1|21:9|2:3|3:2|4:5|5:4|9:16|9:21)$",
        description=(
            "Controls the aspect ratio of the generated image. "
            "Common values: '1:1', '16:9', '9:16', '2:3', '3:2'."
        ),
    )

    seed: int | None = Field(
        default=0,
        ge=0,
        description="Seed for reproducible generation. Set to 0 for a random seed.",
    )

    style_preset: (
        Literal[
            "3d-model",
            "analog-film",
            "anime",
            "cinematic",
            "comic-book",
            "digital-art",
            "enhance",
            "fantasy-art",
            "isometric",
            "line-art",
            "low-poly",
            "modeling-compound",
            "neon-punk",
            "origami",
            "photographic",
            "pixel-art",
            "tile-texture",
        ]
        | None
    ) = Field(
        default=None,
        description="Predefined style preset to guide the image generation. E.g., 'photographic', 'anime'.",
    )
