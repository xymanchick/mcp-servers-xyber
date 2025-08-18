import os
from logging.config import dictConfig

LOGGING_LEVEL = os.getenv("MCP_TELEGRAM_PARSER_LOG_LEVEL", "INFO")

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
            "level": LOGGING_LEVEL,
            "stream": "ext://sys.stdout",
        }
    },
    "root": {"handlers": ["console"], "level": LOGGING_LEVEL},
}


def configure_logging() -> None:
    dictConfig(LOGGING_CONFIG)
