from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class WikipediaConfig(BaseSettings):
    """
    Configuration for the Wikipedia API client.
    Reads from environment variables prefixed with WIKIPEDIA_.
    """
    model_config = SettingsConfigDict(
        env_prefix="WIKIPEDIA_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # A descriptive User-Agent is required by Wikipedia's API etiquette
    user_agent: str = Field(
        default="MCP-Server-Wikipedia/1.0 (https://github.com/your-repo)",
        description="User-Agent header for Wikipedia API requests."
    )
    language: str = Field(
        default="en",
        description="Language edition of Wikipedia to use (e.g., 'en', 'de')."
    )