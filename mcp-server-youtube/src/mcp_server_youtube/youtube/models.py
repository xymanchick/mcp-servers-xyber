from __future__ import annotations

import re
from datetime import datetime
from datetime import timezone
from enum import Enum
from typing import Annotated
from typing import List
from typing import Literal
from typing import Optional

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator
from pydantic.types import StringConstraints
from pydantic_core import PydanticCustomError


class YouTubeVideo(BaseModel):
    """Represents a YouTube video with its metadata and transcript information."""

    video_id: str = Field(..., pattern=r'^[a-zA-Z0-9_-]{11}$')
    title: str
    channel: str
    published_at: datetime
    thumbnail: str
    description: str = ''
    transcript: Optional[str] = None
    transcript_language: Optional[str] = None
    has_transcript: bool = False

    @property
    def url(self) -> str:
        """Returns the YouTube URL for this video."""
        return f'https://www.youtube.com/watch?v={self.video_id}'

    def __str__(self) -> str:
        """Returns a string representation of the YouTubeVideo object."""
        transcript_info = f'Transcript: {self.transcript}\nLanguage: {self.transcript_language}' if self.has_transcript else 'No transcript available'
        return (f'Video ID: {self.video_id}\nTitle: {self.title}\nChannel: {self.channel}\n'
                f'Published at: {self.published_at}\nThumbnail: {self.thumbnail}\n'
                f'Description: {self.description}\n{transcript_info}')


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
        description='List of YouTubeVideo objects containing search results'
    )
    total_results: int = Field(
        default=0,
        description='Total number of results available'
    )
    next_page_token: Optional[str] = Field(
        None,
        description='Token for fetching next page of results'
    )

    model_config = ConfigDict(
        strict=True,
        from_attributes=True,
        extra='forbid',
        populate_by_name=True
    )


# Error codes for validation failures
ERROR_CODES = {
    'QUERY_EMPTY': 'query_empty',
    'QUERY_TOO_LONG': 'query_too_long',
    'INVALID_LANGUAGE': 'invalid_language',
    'INVALID_DATE_FORMAT': 'invalid_date_format',
    'DATE_IN_FUTURE': 'date_in_future',
    'INVALID_ORDER_BY': 'invalid_order_by',
    'INVALID_MAX_RESULTS': 'invalid_max_results',
    'INVALID_VIDEO_ID': 'invalid_video_id',
    'INVALID_URL': 'invalid_url',
    'TEXT_TOO_LONG': 'text_too_long'
}


class LanguageCode(str, Enum):
    """Supported language codes for transcripts.

    Valid values:
    - "en": English
    - "es": Spanish
    - "fr": French
    - "de": German
    - "pt": Portuguese
    - "it": Italian
    - "ja": Japanese
    - "ko": Korean
    - "ru": Russian
    - "zh": Chinese
    """
    ENGLISH = 'en'
    SPANISH = 'es'
    FRENCH = 'fr'
    GERMAN = 'de'
    PORTUGUESE = 'pt'
    ITALIAN = 'it'
    JAPANESE = 'ja'
    KOREAN = 'ko'
    RUSSIAN = 'ru'
    CHINESE = 'zh'


class YouTubeSearchRequest(BaseModel):
    """
    Schema for YouTube search requests.

    Fields:
    - query: Search query string (1-500 characters)
    - max_results: Maximum number of results to return (1-20)
    - transcript_language: Language code for transcript (e.g., 'en', 'es', 'fr')
    - published_after: Only include videos published after this date (ISO format)
    - published_before: Only include videos published before this date (ISO format)
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
        description='Search query string (1-500 characters)'
    )

    max_results: Annotated[int, Field(ge=1, le=20)] = Field(
        default=5,
        description='Maximum number of results to return (1-20). Default: 5'
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
                raise PydanticCustomError(
                    ERROR_CODES['INVALID_LANGUAGE'],
                    f"Invalid language code: {v}. Must be one of: {', '.join(valid_languages)}"
                )
            if not v.isalpha():
                raise PydanticCustomError(
                    ERROR_CODES['INVALID_LANGUAGE'],
                    'Language code must contain only letters'
                )
            try:
                return LanguageCode(v)
            except ValueError:
                raise PydanticCustomError(
                    ERROR_CODES['INVALID_LANGUAGE'],
                    f"Invalid language code: {v}. Must be one of: {', '.join(valid_languages)}"
                )
        return v

    published_after: Optional[Annotated[
        str, StringConstraints(pattern=r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})$')]] = Field(
        None,
        description='Only include videos published after this date (ISO format: YYYY-MM-DDTHH:MM:SSZ or YYYY-MM-DDTHH:MM:SS±HH:MM)'
    )

    order_by: Optional[Literal['relevance', 'date', 'viewCount', 'rating']] = Field(
        None,
        description='Sort order for results. Must be one of: relevance, date, viewCount, rating'
    )

    @field_validator('published_after', 'published_before')
    def validate_dates(cls, v):
        """Validate date format and ensure it's not in the future"""
        if v:
            # First validate the pattern
            if not re.match(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})$', v):
                raise PydanticCustomError(
                    ERROR_CODES['INVALID_DATE_FORMAT'],
                    'Invalid date format. Must be ISO format with timezone'
                )

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
                    raise PydanticCustomError(
                        ERROR_CODES['DATE_IN_FUTURE'],
                        f'Date cannot be in the future (current time: {current_time.isoformat()})'
                    )
            except ValueError as e:
                raise PydanticCustomError(
                    ERROR_CODES['INVALID_DATE_FORMAT'],
                    f'Invalid date: {str(e)}'
                ) from e
        return v

    published_before: Optional[Annotated[
        str, StringConstraints(pattern=r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})$')]] = Field(
        None,
        description='Only include videos published before this date (ISO format: YYYY-MM-DDTHH:MM:SSZ or YYYY-MM-DDTHH:MM:SS±HH:MM)'
    )

    @field_validator('query')
    def validate_query(cls, v):
        """Ensure query is not just whitespace"""
        if v.strip() == '':
            raise PydanticCustomError(
                ERROR_CODES['QUERY_EMPTY'],
                'Query cannot be empty or whitespace only'
            )
        return v
