import os
from logging.config import dictConfig

"""Configures basic logging for the application."""
LOGGING_LEVEL = os.getenv("LOGGING_LEVEL", "INFO")

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
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
            "level": "INFO",
            "stream": "ext://sys.stdout",
        },
    },
    "loggers": {
        "docket": {"level": "WARNING"},
        "fakeredis": {"level": "WARNING"},
        "httpx": {"level": "WARNING"},
        "httpcore": {"level": "WARNING"},
    },
    "root": {"handlers": ["console"], "level": f"{LOGGING_LEVEL}"},
}


def configure_logging():
    """Apply logging configuration."""
    dictConfig(LOGGING_CONFIG)
