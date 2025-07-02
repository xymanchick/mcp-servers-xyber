import re

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Annotated, Literal
from datetime import datetime, timezone
from enum import Enum
from pydantic.types import StringConstraints
from typing_extensions import Annotated
from pydantic_core import PydanticCustomError
from pydantic import ConfigDict


class LanguageCode(str, Enum):
    """Supported language codes for transcripts."""
    ENGLISH = "en"
    SPANISH = "es"
    FRENCH = "fr"
    GERMAN = "de"
    PORTUGUESE = "pt"
    ITALIAN = "it"
    JAPANESE = "ja"
    KOREAN = "ko"
    RUSSIAN = "ru"
    CHINESE = "zh"


class YouTubeSearchRequest(BaseModel):
    """
    Schema for YouTube search requests.

    Fields:
    - query: Search query string (1-500 characters)
    - max_results: Maximum number of results to return (1-20)
    - transcript_language: Language code for transcript (e.g., 'en', 'es', 'fr')
    - published_after: Only include videos published after this date
    - published_before: Only include videos published before this date
    - order_by: Sort order (relevance, date, viewCount, rating)

    Example:
        {
            "query": "python programming",
            "max_results": 5,
            "transcript_language": "en",
            "published_after": "2025-01-01T00:00:00Z",
            "order_by": "relevance"
        }
    """
    model_config = ConfigDict(
        strict=True,
        from_attributes=True,
        extra='forbid',  # Reject any extra fields
        populate_by_name=True
    )

    query: Annotated[str, StringConstraints(min_length=1, max_length=500)] = Field(
        ...,
        description="Search query string (1-500 characters)"
    )
    max_results: Annotated[int, Field(ge=1, le=20)] = Field(
        default=5,
        description="Maximum number of results to return (1-20). Default: 5"
    )
    transcript_language: Optional[str] = Field(
        None,
        description="Language code for transcript (e.g., 'en', 'es', 'fr')"
    )

    @field_validator('transcript_language')
    def validate_language(cls, v):
        """Validate language code format"""
        if v is not None:
            v = v.lower()
            valid_languages = [code.value for code in LanguageCode]
            if v not in valid_languages:
                raise ValueError(f"Invalid language code: {v}. Must be one of: {', '.join(valid_languages)}")
            if not v.isalpha():
                raise ValueError('Language code must contain only letters')
            try:
                return LanguageCode(v)
            except ValueError:
                raise ValueError(f"Invalid language code: {v}. Must be one of: {', '.join(valid_languages)}")
        return v

    published_after: Optional[Annotated[
        str, StringConstraints(pattern=r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})$')]] = Field(
        None,
        description="Only include videos published after this date (ISO format: YYYY-MM-DDTHH:MM:SSZ or YYYY-MM-DDTHH:MM:SS±HH:MM)"
    )

    @field_validator('published_after', 'published_before')
    def validate_dates(cls, v):
        """Validate date format and ensure it's not in the future"""
        if v:
            # First validate the pattern
            if not re.match(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})$', v):
                raise ValueError("Invalid date format. Must be ISO format with timezone")
            
            # Then validate the date logic
            try:
                if v.endswith('Z'):
                    dt_str = v[:-1] + '+00:00'
                else:
                    dt_str = v
                    
                dt = datetime.fromisoformat(dt_str)
                if not dt.tzinfo:
                    dt = dt.replace(tzinfo=timezone.utc)
                
                current_time = datetime.now(timezone.utc)
                if dt > current_time:
                    raise ValueError(f'Date cannot be in the future (current time: {current_time.isoformat()})')
            except ValueError as e:
                raise ValueError(f"Invalid date: {str(e)}") from e
        return v

    published_before: Optional[Annotated[
        str, StringConstraints(pattern=r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})$')]] = Field(
        None,
        description="Only include videos published before this date (ISO format: YYYY-MM-DDTHH:MM:SSZ or YYYY-MM-DDTHH:MM:SS±HH:MM)"
    )

    @field_validator('published_before')
    def validate_published_before(cls, v):
        """Validate date format and ensure it's not in the future"""
        if v:
            # First validate the pattern
            if not re.match(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})$', v):
                raise ValueError("Invalid date format. Must be ISO format with timezone")
            
            # Then validate the date logic
            try:
                if v.endswith('Z'):
                    dt_str = v[:-1] + '+00:00'
                else:
                    dt_str = v
                    
                dt = datetime.fromisoformat(dt_str)
                if not dt.tzinfo:
                    dt = dt.replace(tzinfo=timezone.utc)
                
                current_time = datetime.now(timezone.utc)
                if dt > current_time:
                    raise ValueError(f'Date cannot be in the future (current time: {current_time.isoformat()})')
            except ValueError as e:
                raise ValueError(f"Invalid date: {str(e)}") from e
        return v
    order_by: Optional[Literal['relevance', 'date', 'viewCount', 'rating']] = Field(
        None,
        description="Sort order for search results. Must be one of: relevance, date, viewCount, rating"
    )

    @field_validator('query')
    def validate_query(cls, v):
        """Ensure query is not just whitespace"""
        if v.strip() == '':
            raise PydanticCustomError(
                'query_empty', 
                'Query cannot be empty or whitespace only'
            )
        return v

        try:
            v = datetime.fromisoformat(v)
        except ValueError:
            raise ValueError(
                'Invalid date format. Must be ISO format (YYYY-MM-DDTHH:MM:SSZ or YYYY-MM-DDTHH:MM:SS±HH:MM)')

        # If timezone-naive, assume it's in UTC
        if not v.tzinfo:
            v = v.replace(tzinfo=timezone.utc)
        # Convert to UTC if timezone-aware
        v = v.astimezone(timezone.utc)
        # Compare with current time in UTC
        current_time = datetime.now(timezone.utc)
        if v > current_time:
            raise ValueError(f'Date cannot be in the future (current time: {current_time.isoformat()})')
        return v


class YouTubeVideo(BaseModel):
    """
    Schema for a YouTube video with transcript

    Fields:
    - video_id: YouTube video ID
    - title: Video title
    - channel: Channel name
    - published_at: Video publish date in ISO format
    - thumbnail: Video thumbnail URL
    - description: Video description
    - transcript: Video transcript text (optional)
    """
    video_id: Annotated[str, StringConstraints(pattern=r'^[a-zA-Z0-9_-]{11}$')] = Field(
        ...,
        description="YouTube video ID (11 characters)"
    )
    title: Annotated[str, StringConstraints(max_length=1000)] = Field(
        ...,
        description="Video title"
    )
    channel: Annotated[str, StringConstraints(max_length=1000)] = Field(
        ...,
        description="Channel name"
    )
    published_at: datetime = Field(
        ...,
        description="Video publish date in ISO format"
    )
    thumbnail: Annotated[str, StringConstraints(pattern=r'^https?://')] = Field(
        ...,
        description="Video thumbnail URL"
    )
    description: Annotated[str, StringConstraints(max_length=5000)] = Field(
        ...,
        description="Video description"
    )
    transcript: Optional[str] = Field(
        None,
        description="Video transcript text"
    )


class YouTubeSearchResponse(BaseModel):
    """
    Schema for YouTube search response

    Fields:
    - results: List of matching YouTube videos
    - total_results: Total number of results available
    - next_page_token: Token for next page of results (optional)
    """
    results: Annotated[List[YouTubeVideo], Field(min_length=1)] = Field(
        ...,
        description="List of matching YouTube videos"
    )
    total_results: Annotated[int, Field(ge=0)] = Field(
        ...,
        description="Total number of results available"
    )
    next_page_token: Optional[str] = Field(
        None,
        description="Token for next page of results"
    )

    @field_validator('results')
    def validate_results(cls, v):
        """Ensure results list is not empty"""
        if not v:
            raise ValueError('Results list cannot be empty')
        return v

    @field_validator('total_results')
    def validate_total_results(cls, v, values):
        """Ensure total results matches the number of results returned"""
        if 'results' in values and len(values['results']) != v:
            raise ValueError('Number of results does not match total_results')
        return v


class YouTubeSearchResponseDetailed(BaseModel):
    """
    Schema for YouTube search response.

    Attributes:
        title: Video title
        description: Video description (optional)
        publish_date: Publication date
        transcript: Video transcript (optional)
        video_url: Video URL
        thumbnail_url: Thumbnail URL
        channel_name: Channel name
        channel_url: Channel URL
        view_count: View count (optional)
        like_count: Like count (optional)
        duration: Video duration (optional)
    """
    title: Annotated[str, StringConstraints(min_length=1, max_length=500)] = Field(
        ...,
        description="Title of the YouTube video"
    )
    description: Optional[Annotated[str, StringConstraints(max_length=5000)]] = Field(
        None,
        description="Description of the YouTube video"
    )
    publish_date: datetime = Field(
        ...,
        description="Publication date of the YouTube video"
    )
    transcript: Optional[Annotated[str, StringConstraints(max_length=100000)]] = Field(
        None,
        description="Transcript of the YouTube video"
    )
    video_url: Annotated[
        str, StringConstraints(pattern=r'^https://www\.youtube\.com/watch\?v=[a-zA-Z0-9_-]+$')] = Field(
        ...,
        description="URL of the YouTube video"
    )
    thumbnail_url: Annotated[str, StringConstraints(pattern=r'^https://i\.ytimg\.com/vi/[a-zA-Z0-9_-]+/.*$')] = Field(
        ...,
        description="URL of the video thumbnail"
    )
    channel_name: Annotated[str, StringConstraints(min_length=1, max_length=100)] = Field(
        ...,
        description="Name of the YouTube channel"
    )
    channel_url: Annotated[
        str, StringConstraints(pattern=r'^https://www\.youtube\.com/channel/[a-zA-Z0-9_-]+$')] = Field(
        ...,
        description="URL of the YouTube channel"
    )
    view_count: Optional[Annotated[int, Field(ge=0, le=1000000000)]] = Field(
        None,
        description="Number of views for the video"
    )
    like_count: Optional[Annotated[int, Field(ge=0, le=1000000000)]] = Field(
        None,
        description="Number of likes for the video"
    )
    duration: Optional[Annotated[str, StringConstraints(pattern=r'^PT\d{1,2}H\d{1,2}M\d{1,2}S$')]] = Field(
        None,
        description="Duration of the video in ISO 8601 format"
    )

    @field_validator('transcript')
    def validate_transcript(cls, v):
        """Validate transcript content."""
        if v and len(v) > 100000:
            raise ValueError("Transcript cannot exceed 100,000 characters")
        return v
