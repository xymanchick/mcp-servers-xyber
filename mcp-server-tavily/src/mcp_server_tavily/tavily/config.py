from typing import Any, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# --- Configuration and Error Classes --- #


class TavilyServiceError(Exception):
    """Base exception for Tavily client errors."""

    pass


class TavilyConfigError(TavilyServiceError):
    """Configuration-related errors for Tavily client."""

    pass


class TavilyApiError(TavilyServiceError):
    """Exception raised for errors during Tavily API calls."""

    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(message)
        self.details = details

    def __str__(self) -> str:
        base = super().__str__()
        details_str = f" Details: {self.details}" if self.details else ""
        return f"{base}{details_str}"


class TavilyConfig(BaseSettings):
    """
    Configuration for connecting to the Tavily Search API.
    Reads from environment variables prefixed with TAVILY_.
    """

    model_config = SettingsConfigDict(
        env_prefix="TAVILY_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    api_key: str = Field(...)  # API Key is required

    # Optional Tavily Parameters (provide defaults or allow None)
    max_results: int = Field(default=5, ge=1)
    topic: str = "general"
    search_depth: str = Field(default="basic", pattern="^(basic|advanced)$")
    include_answer: bool = False
    include_raw_content: bool = False
    include_images: bool = False
