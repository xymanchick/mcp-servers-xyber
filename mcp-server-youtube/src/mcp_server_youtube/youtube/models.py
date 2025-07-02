from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class YouTubeVideo(BaseModel):
    """Represents a YouTube video with its metadata and transcript information."""
    
    video_id: str = Field(..., pattern=r'^[a-zA-Z0-9_-]{11}$')
    title: str
    channel: str
    published_at: datetime
    thumbnail: str
    description: str = ""
    transcript: str = ""

    @property
    def url(self) -> str:
        """Returns the YouTube URL for this video."""
        return f"https://www.youtube.com/watch?v={self.video_id}"

    def __str__(self) -> str:
        """Returns a string representation of the YouTubeVideo object."""
        return f"Video ID: {self.video_id}\nTitle: {self.title}\nChannel: {self.channel}\nPublished at: {self.published_at}\nThumbnail: {self.thumbnail}\nDescription: {self.description}\nTranscript: {self.transcript}"
