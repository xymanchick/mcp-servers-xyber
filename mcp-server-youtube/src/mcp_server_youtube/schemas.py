from __future__ import annotations

import re
from datetime import datetime, timezone
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.types import StringConstraints
from pydantic_core import PydanticCustomError


ERROR_CODES = {
    "QUERY_EMPTY": "query_empty",
    "QUERY_TOO_LONG": "query_too_long",
    "INVALID_LANGUAGE": "invalid_language",
    "INVALID_DATE_FORMAT": "invalid_date_format",
    "DATE_IN_FUTURE": "date_in_future",
    "INVALID_ORDER_BY": "invalid_order_by",
    "INVALID_MAX_RESULTS": "invalid_max_results",
    "INVALID_VIDEO_ID": "invalid_video_id",
    "INVALID_URL": "invalid_url",
    "TEXT_TOO_LONG": "text_too_long",
}


class LanguageCode(str, Enum):
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
    """Schema for YouTube search requests."""

    model_config = ConfigDict(
        strict=True, from_attributes=True, extra="forbid", populate_by_name=True
    )

    query: Annotated[str, StringConstraints(min_length=1, max_length=500)] = Field(
        ..., description="Search query string (1-500 characters)"
    )

    max_results: Annotated[int, Field(ge=1, le=20)] = Field(
        default=5, description="Number of results to return (1-20)"
    )

    transcript_language: str | None = Field(
        None, description="Transcript language code (e.g. 'en', 'fr')"
    )

    published_after: (
        Annotated[
            str,
            StringConstraints(
                pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})$"
            ),
        ]
        | None
    ) = Field(None, description="Only include videos after this date (ISO 8601)")

    published_before: (
        Annotated[
            str,
            StringConstraints(
                pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})$"
            ),
        ]
        | None
    ) = Field(None, description="Only include videos before this date (ISO 8601)")

    order_by: Literal["relevance", "date", "viewCount", "rating"] | None = Field(
        None, description="Sort order: relevance, date, viewCount, rating"
    )

    @field_validator("query")
    @classmethod
    def query_not_whitespace(cls, v: str) -> str:
        if not v.strip():
            raise PydanticCustomError(
                ERROR_CODES["QUERY_EMPTY"], "Query cannot be empty or whitespace"
            )
        return v

    @field_validator("transcript_language")
    @classmethod
    def validate_language(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.lower()
        if not v.isalpha():
            raise PydanticCustomError(
                ERROR_CODES["INVALID_LANGUAGE"],
                "Language code must contain only letters",
            )
        if v not in {lang.value for lang in LanguageCode}:
            raise PydanticCustomError(
                ERROR_CODES["INVALID_LANGUAGE"], f"Unsupported language code: {v}"
            )
        return v

    @field_validator("published_after", "published_before")
    @classmethod
    def validate_date_format(cls, v: str | None) -> str | None:
        if not v:
            return None

        if not re.match(
            r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})$", v
        ):
            raise PydanticCustomError(
                ERROR_CODES["INVALID_DATE_FORMAT"], "Invalid ISO 8601 format"
            )

        try:
            dt_str = v.replace("Z", "+00:00")
            dt = datetime.fromisoformat(dt_str)
            dt = dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

            if dt > datetime.now(timezone.utc):
                raise PydanticCustomError(
                    ERROR_CODES["DATE_IN_FUTURE"],
                    f"Date cannot be in the future (now: {datetime.now(timezone.utc).isoformat()})",
                )

        except ValueError as e:
            raise PydanticCustomError(ERROR_CODES["INVALID_DATE_FORMAT"], str(e)) from e

        return v
