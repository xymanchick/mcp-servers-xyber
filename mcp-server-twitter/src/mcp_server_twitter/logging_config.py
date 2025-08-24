import os
import sys
import json
import logging
from logging.config import dictConfig
from typing import Dict, Any
from datetime import datetime

# Get log level from environment with fallback
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# Validate log level
VALID_LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
if LOG_LEVEL not in VALID_LOG_LEVELS:
    LOG_LEVEL = "INFO"

class StructuredFormatter(logging.Formatter):
    """Custom formatter that outputs structured JSON logs."""
    
    def format(self, record: logging.LogRecord) -> str:
        # Base log structure
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
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

class StandardFormatter(logging.Formatter):
    """Human-readable formatter for development."""
    
    def format(self, record: logging.LogRecord) -> str:
        # Color codes for different log levels
        colors = {
            'DEBUG': '\033[36m',    # Cyan
            'INFO': '\033[32m',     # Green  
            'WARNING': '\033[33m',  # Yellow
            'ERROR': '\033[31m',    # Red
            'CRITICAL': '\033[35m', # Magenta
        }
        reset = '\033[0m'
        
        color = colors.get(record.levelname, '')
        
        # Format timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")
        
        # Base format
        base_format = f"{color}[{timestamp}] {record.levelname:8} {record.name}:{record.funcName}:{record.lineno}{reset} - {record.getMessage()}"
        
        # Add extra context if available
        extras = []
        if hasattr(record, 'operation'):
            extras.append(f"op={record.operation}")
        if hasattr(record, 'duration_ms'):
            extras.append(f"duration={record.duration_ms}ms")
        if hasattr(record, 'user_id'):
            extras.append(f"user={record.user_id}")
        if hasattr(record, 'tweet_id'):
            extras.append(f"tweet={record.tweet_id}")
            
        if extras:
            base_format += f" [{', '.join(extras)}]"
        
        # Add exception if present
        if record.exc_info:
            base_format += f"\n{self.formatException(record.exc_info)}"
            
        return base_format

# Determine output format based on environment
STRUCTURED_LOGGING = os.getenv("STRUCTURED_LOGGING", "false").lower() in ("true", "1", "yes")
USE_JSON_LOGS = os.getenv("JSON_LOGS", "false").lower() in ("true", "1", "yes")

# Choose formatter based on environment
if USE_JSON_LOGS or STRUCTURED_LOGGING:
    formatter_class = StructuredFormatter
    format_string = None  # Not used with custom formatter
else:
    formatter_class = StandardFormatter
    format_string = None  # Not used with custom formatter

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "structured": {
            "()": StructuredFormatter,
        },
        "standard": {
            "()": StandardFormatter,
        },
        "simple": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "structured" if (USE_JSON_LOGS or STRUCTURED_LOGGING) else "standard",
            "level": LOG_LEVEL,
            "stream": "ext://sys.stdout",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "structured",
            "filename": "mcp_twitter_server.log",
            "maxBytes": 50 * 1024 * 1024,  # 50MB
            "backupCount": 10,
            "level": LOG_LEVEL,
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
            "level": LOG_LEVEL,
            "handlers": ["console", "file"],
            "propagate": False,
        },
        "mcp_server_twitter.server": {
            "level": LOG_LEVEL,
            "handlers": ["console", "file"],
            "propagate": False,
        },
        "mcp_server_twitter.twitter": {
            "level": LOG_LEVEL,
            "handlers": ["console", "file"],
            "propagate": False,
        },
        "tweepy": {
            "level": "WARNING",  # Reduce noise from tweepy
            "handlers": ["console", "file"],
            "propagate": False,
        },
        "aiohttp": {
            "level": "WARNING",  # Reduce noise from aiohttp
            "handlers": ["console", "file"],
            "propagate": False,
        },
    },
    "root": {
        "handlers": ["console", "error_file"], 
        "level": LOG_LEVEL
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

def configure_logging():
    """Apply enhanced logging configuration."""
    os.makedirs(os.path.dirname("mcp_twitter_server.log"), exist_ok=True) 
    dictConfig(LOGGING_CONFIG)
    
    # Log the configuration
    logger = logging.getLogger("mcp_server_twitter.logging")
    logger.info(
        f"Logging configured - Level: {LOG_LEVEL}, Structured: {STRUCTURED_LOGGING}, JSON: {USE_JSON_LOGS}"
    )

def get_logger(name: str, **context) -> TwitterLoggerAdapter:
    """Get a configured logger with optional context."""
    base_logger = logging.getLogger(name)
    return TwitterLoggerAdapter(base_logger, context)

def log_performance(logger: logging.Logger, operation: str, duration_ms: float, **context):
    """Log performance metrics in a structured way."""
    extra = {
        'operation': operation,
        'duration_ms': round(duration_ms, 2),
        **context
    }
    
    if duration_ms > 5000:  # > 5 seconds
        logger.warning(f"Slow operation: {operation} took {duration_ms:.2f}ms", extra=extra)
    elif duration_ms > 1000:  # > 1 second
        logger.info(f"Operation completed: {operation} took {duration_ms:.2f}ms", extra=extra)
    else:
        logger.debug(f"Operation completed: {operation} took {duration_ms:.2f}ms", extra=extra)

# Export the current log level for other modules
logging_level = LOG_LEVEL