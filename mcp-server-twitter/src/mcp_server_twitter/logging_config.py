import os
import sys
import json
import logging
from logging.config import dictConfig
from typing import Dict, Any, Literal
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Get log level from environment
logging_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = (
    os.getenv("LOGGING_LEVEL", "INFO").upper()
)


class StructuredFormatter(logging.Formatter):
    """Custom formatter that outputs structured JSON logs."""

    def format(self, record: logging.LogRecord) -> str:
        # Base log structure
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Add extra fields from LoggerAdapter or custom fields
        if hasattr(record, 'extra_fields'):
            log_entry.update(record.extra_fields)

        # Add performance metrics if present
        if hasattr(record, 'duration_ms'):
            log_entry["duration_ms"] = record.duration_ms

        if hasattr(record, 'operation'):
            log_entry["operation"] = record.operation

        if hasattr(record, 'user_id'):
            log_entry["user_id"] = record.user_id

        if hasattr(record, 'tweet_id'):
            log_entry["tweet_id"] = record.tweet_id

        return json.dumps(log_entry, ensure_ascii=False)


LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "structured": {
            "()": StructuredFormatter,
        },
        "simple": {
            "format": "%%(asctime)s - %%(name)s - %%(levelname)s - %%(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "structured",
            "level": logging_level,
            "stream": "ext://sys.stdout",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "structured",
            "filename": "mcp_twitter_server.log",
            "maxBytes": 50 * 1024 * 1024,  # 50MB
            "backupCount": 10,
            "level": logging_level,
        },
        "error_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "structured",
            "filename": "mcp_twitter_errors.log",
            "maxBytes": 10 * 1024 * 1024,  # 10MB
            "backupCount": 5,
            "level": "ERROR",
        },
    },
    "loggers": {
        "mcp_server_twitter": {
            "level": logging_level,
            "handlers": ["console", "file"],
            "propagate": False,
        },
    },
    "root": {
        "handlers": ["console", "error_file"],
        "level": logging_level
    },
}


class TwitterLoggerAdapter(logging.LoggerAdapter):
    """Custom logger adapter for Twitter operations with structured context."""

    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
        """Add extra context to log records."""
        extra = kwargs.get('extra', {})

        # Merge adapter context with record-specific extra
        if self.extra:
            extra.update(self.extra)

        kwargs['extra'] = extra
        return msg, kwargs


def log_retry_attempt(retry_state):
    """Enhanced retry logging with comprehensive context and rate limiting."""
    
    # Extract retry context
    attempt_number = retry_state.attempt_number
    outcome = retry_state.outcome
    next_action = retry_state.next_action
    
    # Get the original exception for context
    exception = None
    if outcome and outcome.failed:
        exception = outcome.exception()
    
    # Calculate time until next retry
    next_sleep = None
    if next_action and hasattr(next_action, 'sleep'):
        next_sleep = round(next_action.sleep, 2)
    
    # Extract operation context from the function being retried
    operation_name = "unknown_operation"
    if hasattr(retry_state.fn, '__name__'):
        operation_name = retry_state.fn.__name__
    
    # Determine if this is approaching final attempts
    is_approaching_final = attempt_number >= 3  # Log more frequently near the end
    
    # Create structured log context
    retry_context = {
        'operation': operation_name,
        'attempt_number': attempt_number,
        'retry_reason': str(exception) if exception else 'Unknown error',
        'exception_type': type(exception).__name__ if exception else None,
        'next_sleep_seconds': next_sleep,
        'total_elapsed_time': getattr(retry_state, 'seconds_since_start', None)
    }
    
    # Rate limiting for retry logs to prevent flooding
    # Use a simple approach - only log every few attempts for the same operation
    should_log_attempt = (
        attempt_number == 1 or  # Always log first retry
        attempt_number % 3 == 0 or  # Log every 3rd attempt
        is_approaching_final or  # Log more frequently near the end
        (next_sleep and next_sleep >= 5)  # Log if waiting 5+ seconds
    )
    
    if should_log_attempt:
        logger.warning(
            f"Retrying {operation_name} after failure (attempt {attempt_number})",
            extra=retry_context
        )
    else:
        # Still log at debug level for full traceability
        logger.debug(
            f"Retry attempt {attempt_number} for {operation_name} (rate-limited)",
            extra=retry_context
        )

def configure_logging():
    """Apply enhanced logging configuration."""
    # Ensure log directories exist
    for handler_config in LOGGING_CONFIG.get("handlers", {}).values():
        if "filename" in handler_config:
            log_filename = handler_config["filename"]
            log_dir = os.path.dirname(log_filename)
            if log_dir:
                os.makedirs(log_dir, exist_ok=True)

    dictConfig(LOGGING_CONFIG)

    logger = logging.getLogger("mcp_server_twitter.logging")
    logger.info(
        f"Logging configured - Level: {logging_level}, Structured: {True}, JSON: {False}"
    )


def get_logger(name: str, **context) -> TwitterLoggerAdapter:
    """Get a configured logger with optional context."""
    base_logger = logging.getLogger(name)
    return TwitterLoggerAdapter(base_logger, context)
