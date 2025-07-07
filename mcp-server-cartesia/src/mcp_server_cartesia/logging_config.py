import logging
import os
from logging.config import dictConfig

"""Configures basic logging for the application."""
# Use specific env var prefix if desired, or keep generic
logging_level = os.getenv("MCP_CARTESIA_LOG_LEVEL", "INFO").upper()
log_file_path = os.getenv(
    "MCP_CARTESIA_LOG_FILE", "app.log"
)  # Allow configuring log file path

# Ensure log directory exists if a path is specified
log_dir = os.path.dirname(log_file_path)
if log_dir and not os.path.exists(log_dir):
    try:
        os.makedirs(log_dir)
    except OSError as e:
        print(
            f"Warning: Could not create log directory '{log_dir}'. Logging to file might fail. Error: {e}"
        )
        log_file_path = "app.log"  # Fallback to current dir

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
            "level": "INFO",  # Console logs INFO and above by default
            "stream": "ext://sys.stdout",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "standard",
            "filename": log_file_path,  # Log file name
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "level": "DEBUG",  # File logs DEBUG and above by default
        },
    },
    "root": {
        "handlers": ["console", "file"],
        "level": f"{logging_level}",  # Overall level set by env var
    },
    # Configure logging for specific libraries if needed
    "loggers": {
        "uvicorn.error": {
            "level": "INFO",  # Example: Control uvicorn error level
            "handlers": ["console", "file"],
            "propagate": False,
        },
        "uvicorn.access": {
            "level": "WARNING",  # Example: Reduce access log noise
            "handlers": ["console", "file"],
            "propagate": False,
        },
        "cartesia": {  # Example: Control Cartesia library logging level
            "level": "INFO",
            "handlers": ["console", "file"],
            "propagate": False,
        },
    },
}


def configure_logging():
    """Apply logging configuration."""
    try:
        dictConfig(LOGGING_CONFIG)
        logging.getLogger(__name__).info(
            f"Logging configured. Level: {logging_level}, File: {log_file_path}"
        )
    except Exception as e:
        # Fallback to basic config if dictConfig fails (e.g., file permission issue)
        logging.basicConfig(
            level=logging_level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        logging.getLogger(__name__).error(
            f"Failed to apply dictionary logging config: {e}. Falling back to basic config.",
            exc_info=True,
        )
