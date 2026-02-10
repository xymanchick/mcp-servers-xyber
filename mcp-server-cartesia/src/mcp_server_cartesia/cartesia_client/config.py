import os
from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict

# --- Configuration and Error Classes --- #


class CartesiaClientError(Exception):
    """Base exception for Cartesia client errors."""

    pass


class CartesiaConfigError(CartesiaClientError):
    """Configuration-related errors for Cartesia client."""

    pass


class CartesiaApiError(CartesiaClientError):
    """Exception raised for errors during Cartesia API calls."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        details: Any | None = None,
    ):
        super().__init__(message)
        self.status_code = status_code  # Store status if available from API response
        self.details = details

    def __str__(self) -> str:
        base = super().__str__()
        status_str = f" (HTTP Status: {self.status_code})" if self.status_code else ""
        details_str = f" Details: {self.details}" if self.details else ""
        return f"{base}{status_str}{details_str}"


class CartesiaConfig(BaseSettings):
    """
    Configuration for connecting to the Cartesia API.
    Reads from environment variables prefixed with CARTESIA_.
    """

    model_config = SettingsConfigDict(
        env_prefix="CARTESIA_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    api_key: str  # API Key is required
    voice_id: str = "a38e4e85-e815-43ab-acf1-907c4688dd6c"  # Default voice
    model_id: str = "sonic-2"  # Default model sonic-2
    output_dir: str = "/app/audio_outputs"

    # Define the default output format here or allow overriding via tool input?
    # For now, keep it similar to the original script
    output_format_container: str = "wav"
    output_format_encoding: str = "pcm_f32le"
    output_format_sample_rate: int = 44100

    @property
    def output_format(self) -> dict:
        """Returns the output format dictionary."""
        return {
            "container": self.output_format_container,
            "encoding": self.output_format_encoding,
            "sample_rate": self.output_format_sample_rate,
        }

    # Ensure output directory exists when config is loaded
    def __init__(self, **values):
        super().__init__(**values)
        # Create audio directory relative to the mcp_server_cartesia package
        import mcp_server_cartesia

        package_dir = os.path.dirname(os.path.abspath(mcp_server_cartesia.__file__))
        abs_output_dir = os.path.join(package_dir, self.output_dir)
        try:
            os.makedirs(abs_output_dir, exist_ok=True)
            # Store the absolute path for internal use
            self._abs_output_dir = abs_output_dir
        except OSError as e:
            # Log or raise a more specific config error if directory creation fails
            raise CartesiaConfigError(
                f"Failed to create Cartesia output directory '{abs_output_dir}': {e}"
            ) from e

    @property
    def absolute_output_dir(self) -> str:
        return self._abs_output_dir
