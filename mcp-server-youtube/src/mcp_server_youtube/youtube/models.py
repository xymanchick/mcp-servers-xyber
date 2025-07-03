from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Literal
from datetime import datetime
from pydantic.types import StringConstraints


class YouTubeVideo(BaseModel):
    """Represents a YouTube video with its metadata and transcript information."""
    
    video_id: str = Field(..., pattern=r'^[a-zA-Z0-9_-]{11}$')
    title: str
    channel: str
    published_at: datetime
    thumbnail: str
    description: str = ""
    transcript: Optional[str] = None
    transcript_language: Optional[str] = None
    has_transcript: bool = False

    @property
    def url(self) -> str:
        """Returns the YouTube URL for this video."""
        return f"https://www.youtube.com/watch?v={self.video_id}"

    def __str__(self) -> str:
        """Returns a string representation of the YouTubeVideo object."""
        transcript_info = f"Transcript: {self.transcript}\nLanguage: {self.transcript_language}" if self.has_transcript else "No transcript available"
        return f"Video ID: {self.video_id}\nTitle: {self.title}\nChannel: {self.channel}\nPublished at: {self.published_at}\nThumbnail: {self.thumbnail}\nDescription: {self.description}\n{transcript_info}"


class YouTubeSearchResponse(BaseModel):
    """
    Schema for YouTube search response.
    
    Fields:
        videos: List of YouTubeVideo objects containing search results
        total_results: Total number of results available
        next_page_token: Token for fetching next page of results
    """
    videos: List[YouTubeVideo] = Field(
        default=[],
        description="List of YouTubeVideo objects containing search results"
    )
    total_results: int = Field(
        default=0,
        description="Total number of results available"
    )
    next_page_token: Optional[str] = Field(
        None,
        description="Token for fetching next page of results"
    )

    model_config = ConfigDict(
        strict=True,
        from_attributes=True,
        extra='forbid',
        populate_by_name=True
    )
