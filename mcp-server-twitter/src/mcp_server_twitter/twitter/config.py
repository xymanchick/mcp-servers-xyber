from pydantic_settings import BaseSettings, SettingsConfigDict


class TwitterConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="TWITTER_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    API_KEY: str
    API_SECRET_KEY: str
    ACCESS_TOKEN: str
    ACCESS_TOKEN_SECRET: str
    BEARER_TOKEN: str
    media_upload_enabled: bool = True
    max_tweet_length: int = 280
    poll_max_options: int = 4
    poll_max_duration: int = 10080
