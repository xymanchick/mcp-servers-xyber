from pydantic import BaseModel, Field


class GenerateImageRequest(BaseModel):
    """Input schema for the generate_image tool."""

    prompt: str = Field(
        ..., max_length=100, description="Text prompt describing the desired image"
    )
    width: int = Field(
        512,
        ge=128,
        le=1024,
        multiple_of=8,
        description="Image width in pixels (128-1024, divisible by 8)",
    )
    height: int = Field(
        512,
        ge=128,
        le=1024,
        multiple_of=8,
        description="Image height in pixels (128-1024, divisible by 8)",
    )
    num_images: int = Field(
        1, ge=1, le=4, description="Number of images to generate (1-4)"
    )
    seed: int | None = Field(None, description="Seed for reproducible generation")
    guidance_scale: float = Field(
        7.5, ge=1.0, le=20.0, description="Prompt guidance scale (1.0-20.0)"
    )
    num_inference_steps: int = Field(
        50, ge=10, le=100, description="Number of denoising steps (10-100)"
    )
