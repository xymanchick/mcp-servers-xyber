from pydantic_settings import BaseSettings, SettingsConfigDict

# --- Configuration and Error Classes --- #


class StableDiffusionClientError(Exception):
    """Base class for Stable Diffusion client-related errors."""

    pass


class StableDiffusionServerConnectionError(StableDiffusionClientError):
    """Error while connecting to the Stable Diffusion server."""

    pass


class StableDiffusionClientConfig(BaseSettings):
    """
    Settings for Stable Diffusion client configuration.
    Configuration can be provided via environment variables:
    STABLE_DIFFUSION_SERVERS_URL=https://api.stability.ai/v2beta/stable-image/generate/core
    STABLE_DIFFUSION_SERVERS_API_KEY=your_api_key
    """

    model_config = SettingsConfigDict(
        env_prefix="STABLE_DIFFUSION_", extra="ignore", env_file=".env"
    )

    url: str = "https://api.stability.ai/v2beta/stable-image/generate/core"
    api_key: str
