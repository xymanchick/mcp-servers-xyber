from pydantic import BaseModel, Field


class PostToTelegramRequest(BaseModel):
    """Input schema for the post_to_telegram tool."""

    message: str = Field(
        ...,
        min_length=1,
        max_length=4096,
        description="The message content to post to Telegram",
    )
