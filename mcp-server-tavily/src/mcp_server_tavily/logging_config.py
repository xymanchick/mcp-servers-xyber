from __future__ import annotations

from logging.config import dictConfig

from pydantic_settings import BaseSettings, SettingsConfigDict


class _LoggingSettings(BaseSettings):
    """Configuration to be used for logging across the MCP server."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    LOGGING_LEVEL: str = "INFO"


_logging_settings = _LoggingSettings()

logging_level = _logging_settings.LOGGING_LEVEL

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,  # Preserve existing loggers
    "formatters": {
        "standard": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
            "stream": "ext://sys.stdout",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "standard",
            "filename": "app.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
        },
    },
    "root": {"handlers": ["console"], "level": f"{_logging_settings.LOGGING_LEVEL}"},
    # Adjust module specific loggers as needed
    "loggers": {
        # "uvicorn.error": {
        #     "handlers": ["console"],
        #     "level": logging_level,
        #     "propagate": False,
        # },
        # "uvicorn.access": {
        #     "handlers": ["console"],
        #     "level": logging_level,
        #     "propagate": False,
        # },
        # "fastapi": {
        #     "handlers": ["console"],
        #     "level": logging_level,
        #     "propagate": False,
        # }
    }
}


def configure_logging():
    """Apply logging configuration."""
    dictConfig(LOGGING_CONFIG)
