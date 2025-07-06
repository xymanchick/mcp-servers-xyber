import logging

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# --- Configuration and Error Classes --- #


class GoogleServiceError(Exception):
    """Base class for Google service-related errors."""

    pass


class GoogleConfigError(GoogleServiceError):
    """Configuration-related errors for Google client."""

    pass


class GoogleAPIError(GoogleServiceError):
    """Errors during Google API operations."""

    pass


class EmptyPredictionError(GoogleAPIError):
    """API operation returned an empty prediction result."""

    pass


class GoogleConfig(BaseSettings):
    """
    Configuration for connecting to Google Vertex AI services.
    Reads from environment variables prefixed with GOOGLE_.
    """

    model_config = SettingsConfigDict(
        env_prefix="GOOGLE_",
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
        case_sensitive=False,
    )

    # Project info
    project_id: str
    location: str
    endpoint_id: str
    api_endpoint: str

    # Credentials info as a dictionary
    credentials_type: str
    credentials_project_id: str
    credentials_private_key_id: str
    credentials_private_key: str
    credentials_client_email: str
    credentials_client_id: str
    credentials_auth_uri: str
    credentials_token_uri: str
    credentials_auth_provider_x509_cert_url: str
    credentials_client_x509_cert_url: str
    credentials_universe_domain: str

    @field_validator("credentials_private_key")
    @classmethod
    def clean_private_key(cls, v: str) -> str:
        """
        Cleans the Google service account private key string from environment variables.

        Hint:
        GOOGLE_CREDENTIALS_PRIVATE_KEY = "-----BEGIN PRIVATE KEY-----\n....\n-----END PRIVATE KEY-----"

        Handles differences between docker compose env_file and docker run --env-file:
        1. Removes surrounding quotes if present.
        2. Replaces literal '\\n' sequences with actual newline characters.

        """
        # 1. Remove surrounding double quotes if they exist
        if v.startswith('"') and v.endswith('"'):
            v = v[1:-1]
            logger.debug("Removed surrounding double quotes.")

        # 2. Replace literal backslash-n with actual newline character
        if "\\n" in v:
            v = v.replace("\\n", "\n")
            logger.debug("Replaced literal '\\n' with actual newline '\n'.")

        return v

    @property
    def credentials_info(self) -> dict[str, str]:
        """Get credentials as a dictionary"""
        return {
            "type": self.credentials_type,
            "project_id": self.credentials_project_id,
            "private_key_id": self.credentials_private_key_id,
            "private_key": self.credentials_private_key,
            "client_email": self.credentials_client_email,
            "client_id": self.credentials_client_id,
            "auth_uri": self.credentials_auth_uri,
            "token_uri": self.credentials_token_uri,
            "auth_provider_x509_cert_url": self.credentials_auth_provider_x509_cert_url,
            "client_x509_cert_url": self.credentials_client_x509_cert_url,
            "universe_domain": self.credentials_universe_domain,
        }
