import os
from logging.config import dictConfig

"""Configures basic logging for the application."""
logging_level = os.getenv("LOGGING_LEVEL", "INFO")

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
            "level": logging_level,
            "stream": "ext://sys.stdout",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "standard",
            "filename": "app.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "level": logging_level, # for dyanamic configuration ...
        },
    },
    "root": {"handlers": ["console", "file"], "level": f"{logging_level}"},
}


def configure_logging():
    """Apply logging configuration."""
    dictConfig(LOGGING_CONFIG)
