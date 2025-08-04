from __future__ import annotations

import os
from logging.config import dictConfig

"""
Configures logging for the YouTube MCP server with proper granularity.

Environment Variables:
- LOG_LEVEL: Controls the overall logging verbosity (DEBUG, INFO, WARNING, ERROR)
- LOGGING_LEVEL: Backward compatibility (deprecated, use LOG_LEVEL instead)

Log Levels:
- DEBUG: Detailed internal steps, request payloads, raw API responses
- INFO: Lifecycle events (server start, successful operations, search results)
- WARNING: Unexpected but recoverable situations (missing video IDs, fallback actions)
- ERROR: Failures, exceptions, and unrecoverable errors
"""

# Support both LOG_LEVEL (preferred) and LOGGING_LEVEL (backward compatibility)
log_level = os.getenv('LOG_LEVEL', os.getenv('LOGGING_LEVEL', 'INFO')).upper()

# Validate log level
valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
if log_level not in valid_levels:
    print(f"Warning: Invalid log level '{log_level}'. Using 'INFO' as default.")
    log_level = 'INFO'

LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,  # Preserve existing loggers
    'formatters': {
        'standard': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
        'detailed': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s() - %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
            'level': log_level,  # Dynamic level based on environment
            'stream': 'ext://sys.stdout',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'detailed' if log_level == 'DEBUG' else 'standard',
            'filename': os.getenv('LOG_FILE', 'youtube_mcp.log'),   # LOG_FILE: Path to the file where logs are written (optional)
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'level': 'DEBUG',  # File always captures DEBUG and above
        },
        'error_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'detailed',
            'filename': 'errors.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 3,
            'level': 'ERROR',
        },
    },
    'loggers': {
        # YouTube MCP specific loggers
        'mcp_server_youtube': {
            'level': log_level,
            'handlers': ['console', 'file','error_file'],
            'propagate': False,
        },
        # External library loggers with controlled verbosity
        'googleapiclient': {
            'level': 'WARNING',  # Reduce Google API client noise
            'handlers': ['console', 'file'],
            'propagate': False,
        },
        'youtube_transcript_api': {
            'level': 'WARNING',  # Reduce transcript API noise
            'handlers': ['console', 'file'],
            'propagate': False,
        },
        'uvicorn.error': {
            'level': 'INFO',
            'handlers': ['console', 'file'],
            'propagate': False,
        },
        'uvicorn.access': {
            'level': 'WARNING' if log_level != 'DEBUG' else 'INFO',
            'handlers': ['console', 'file'],
            'propagate': False,
        },
    },
    'root': {
        'handlers': ['console', 'error_file'] if log_level in ['WARNING', 'ERROR'] else ['console', 'file'],
        'level': log_level,
    },
}


def configure_logging():
    """
    Apply logging configuration with proper granularity.
    
    This function sets up logging with different verbosity levels:
    - DEBUG: Shows all internal operations, API calls, and detailed tracing
    - INFO: Shows normal operations, startup/shutdown, and search results
    - WARNING: Shows unexpected but recoverable situations
    - ERROR: Shows only failures and critical issues
    """
    try:
        dictConfig(LOGGING_CONFIG)
        
        # Log the configuration being used
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Logging configured with level: {log_level}")
        
        if log_level == 'DEBUG':
            logger.debug("Debug logging enabled - detailed internal operations will be logged")
        elif log_level == 'INFO':
            logger.info("Info logging enabled - normal operations and lifecycle events will be logged")
        elif log_level == 'WARNING':
            logger.warning("Warning logging enabled - only warnings and errors will be logged")
        elif log_level == 'ERROR':
            logger.error("Error logging enabled - only errors will be logged")
            
    except Exception as e:
        # Fallback to basic config if dictConfig fails
        import logging
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        print(f"Warning: Failed to apply detailed logging config: {e}. Using basic configuration.")


def get_current_log_level() -> str:
    """Return the current configured log level."""
    return log_level
