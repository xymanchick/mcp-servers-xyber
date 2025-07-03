from __future__ import annotations

import re
from datetime import datetime
from datetime import timezone
from enum import Enum
from typing import Annotated
from typing import Literal

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
    transcript: str | None = None
    transcript_language: str | None = None
    has_transcript: bool = False

    @property
    def url(self) -> str:
        return f'https://www.youtube.com/watch?v={self.video_id}'

    def __str__(self) -> str:
        transcript_info = (
            f'Transcript: {self.transcript}\nLanguage: {self.transcript_language}'
            if self.has_transcript else 'No transcript available'
        )
        return (
            f'Video ID: {self.video_id}\nTitle: {self.title}\nChannel: {self.channel}\n'
            f'Published at: {self.published_at}\nThumbnail: {self.thumbnail}\n'
            f'Description: {self.description}\n{transcript_info}'
        )


class YouTubeSearchResponse(BaseModel):
    """Schema for YouTube search response."""
    videos: list[YouTubeVideo] = Field(default=[], description='List of search results')
    total_results: int = Field(default=0, description='Total number of results')
    next_page_token: str | None = Field(None, description='Token for next page')

    model_config = ConfigDict(
        strict=True,
        from_attributes=True,
        extra='forbid',
        populate_by_name=True
    )


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
    """Schema for YouTube search requests."""
    model_config = ConfigDict(
        strict=True,
        from_attributes=True,
        extra='forbid',
        populate_by_name=True
    )

    query: Annotated[
        str,
        StringConstraints(min_length=1, max_length=500)
    ] = Field(..., description='Search query string (1-500 characters)')

    max_results: Annotated[int, Field(ge=1, le=20)] = Field(
        default=5, description='Number of results to return (1-20)'
    )

    transcript_language: str | None = Field(
        None, description="Transcript language code (e.g. 'en', 'fr')"
    )

    published_after: Annotated[
        str, StringConstraints(pattern=r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})$')
    ] | None = Field(
        None,
        description='Only include videos after this date (ISO 8601)'
    )

    published_before: Annotated[
        str, StringConstraints(pattern=r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})$')
    ] | None = Field(
        None,
        description='Only include videos before this date (ISO 8601)'
    )

    order_by: Literal['relevance', 'date', 'viewCount', 'rating'] | None = Field(
        None, description='Sort order: relevance, date, viewCount, rating'
    )

    @field_validator('query')
    @classmethod
    def query_not_whitespace(cls, v: str) -> str:
        if not v.strip():
            raise PydanticCustomError(ERROR_CODES['QUERY_EMPTY'], 'Query cannot be empty or whitespace')
        return v

    @field_validator('transcript_language')
    @classmethod
    def validate_language(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.lower()
        if not v.isalpha():
            raise PydanticCustomError(ERROR_CODES['INVALID_LANGUAGE'], 'Language code must contain only letters')
        if v not in {lang.value for lang in LanguageCode}:
            raise PydanticCustomError(ERROR_CODES['INVALID_LANGUAGE'], f'Unsupported language code: {v}')
        return v

    @field_validator('published_after', 'published_before')
    @classmethod
    def validate_date_format(cls, v: str | None) -> str | None:
        if not v:
            return None

        if not re.match(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})$', v):
            raise PydanticCustomError(ERROR_CODES['INVALID_DATE_FORMAT'], 'Invalid ISO 8601 format')

        try:
            dt_str = v.replace('Z', '+00:00')
            dt = datetime.fromisoformat(dt_str)
            dt = dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

            if dt > datetime.now(timezone.utc):
                raise PydanticCustomError(
                    ERROR_CODES['DATE_IN_FUTURE'],
                    f'Date cannot be in the future (now: {datetime.now(timezone.utc).isoformat()})'
                )

        except ValueError as e:
            raise PydanticCustomError(ERROR_CODES['INVALID_DATE_FORMAT'], str(e)) from e

        return v
