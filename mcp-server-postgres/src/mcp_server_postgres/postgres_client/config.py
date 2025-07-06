from pydantic_settings import BaseSettings, SettingsConfigDict

# --- Configuration and Error Classes --- #


class PostgresServiceError(Exception):
    """Base class for PostgreSQL service-related errors."""

    pass


class PostgresConfigError(PostgresServiceError):
    """Configuration-related errors for PostgreSQL client."""

    pass


class PostgresAPIError(PostgresServiceError):
    """Errors during PostgreSQL database operations."""

    pass


class PostgresConfig(BaseSettings):
    """Configuration for PostgreSQL connection"""

    model_config = SettingsConfigDict(
        env_prefix="POSTGRES_",
        env_file=None,  # No default .env file, only use environment variables
        env_nested_delimiter="__",
        extra="ignore",
        case_sensitive=False,
    )

    host: str
    port: int = 5432
    user: str
    password: str
    database_name: str
    min_connections: int = 1
    max_connections: int = 10
    connection_timeout: float = 60.0
    command_timeout: float = 30.0

    def get_db_url(self):
        return (
            f"postgresql+asyncpg://{self.user}:{self.password}@"
            f"{self.host}:{self.port}/{self.database_name}"
        )
