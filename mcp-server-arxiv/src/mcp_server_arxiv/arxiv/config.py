import logging
from typing import Any, Optional

from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# --- Configuration and Error Classes --- #


class ArxivServiceError(Exception):
    """Base exception for ArXiv service errors."""

    pass


class ArxivConfigError(ArxivServiceError):
    """Configuration-related errors for ArXiv service."""

    pass


class ArxivApiError(ArxivServiceError):
    """Exception raised for errors during ArXiv API calls or processing."""

    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(message)
        self.details = details

    def __str__(self) -> str:
        base = super().__str__()
        details_str = f" Details: {self.details}" if self.details else ""
        return f"{base}{details_str}"


class ArxivConfig(BaseSettings):
    """
    Configuration for the ArXiv Search Service.
    Reads from environment variables prefixed with ARXIV_.
    """

    model_config = SettingsConfigDict(
        env_prefix="ARXIV_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    default_max_results: int = Field(default=5, ge=1, le=50)
    default_max_text_length: Optional[int] = Field(
        default=None, ge=100
    )  # Optional limit, min 100 chars if set

    def __init__(self, **values: Any):
        try:
            super().__init__(**values)
            logger.info("ArxivConfig loaded successfully.")
            logger.debug(
                f"Arxiv Config: MaxResultsDefault={self.default_max_results}, MaxTextLengthDefault={self.default_max_text_length}"
            )
        except ValidationError as e:
            logger.error(f"Arxiv configuration validation failed: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"Unexpected error loading ArxivConfig: {e}", exc_info=True)
