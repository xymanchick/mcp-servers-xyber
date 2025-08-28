# errors.py - Custom error classes for better error handling and logging
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class TwitterMCPError(Exception):
    """Base exception for all Twitter MCP server errors."""
    
    def __init__(
        self, 
        message: str, 
        error_code: str = "TWITTER_MCP_ERROR",
        context: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.context = context or {}
        self.original_exception = original_exception
        
        # Log the error with structured context
        logger.error(
            f"TwitterMCPError: {message}",
            extra={
                'error_code': error_code,
                'error_context': context,
                'original_exception': str(original_exception) if original_exception else None
            },
            exc_info=original_exception is not None
        )

class TwitterAPIError(TwitterMCPError):
    """Exception for Twitter API related errors."""
    
    def __init__(
        self, 
        message: str, 
        status_code: Optional[int] = None,
        error_code: str = "TWITTER_API_ERROR",
        context: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None
    ):
        self.status_code = status_code
        context = context or {}
        if status_code:
            context['status_code'] = status_code
            
        super().__init__(message, error_code, context, original_exception)

class TwitterAuthenticationError(TwitterAPIError):
    """Exception for Twitter authentication/authorization errors."""
    
    def __init__(
        self, 
        message: str = "Twitter authentication failed",
        context: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None
    ):
        super().__init__(
            message, 
            status_code=401,
            error_code="TWITTER_AUTH_ERROR",
            context=context,
            original_exception=original_exception
        )

class TwitterRateLimitError(TwitterAPIError):
    """Exception for Twitter rate limit errors."""
    
    def __init__(
        self, 
        message: str = "Twitter API rate limit exceeded",
        retry_after: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None
    ):
        context = context or {}
        if retry_after:
            context['retry_after_seconds'] = retry_after
            
        super().__init__(
            message,
            status_code=429,
            error_code="TWITTER_RATE_LIMIT_ERROR",
            context=context,
            original_exception=original_exception
        )

class TwitterForbiddenError(TwitterAPIError):
    """Exception for Twitter forbidden/permission errors."""
    
    def __init__(
        self, 
        message: str = "Twitter API access forbidden",
        context: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None
    ):
        super().__init__(
            message,
            status_code=403,
            error_code="TWITTER_FORBIDDEN_ERROR",
            context=context,
            original_exception=original_exception
        )

class TwitterNotFoundError(TwitterAPIError):
    """Exception for Twitter resource not found errors."""
    
    def __init__(
        self, 
        message: str = "Twitter resource not found",
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None
    ):
        context = context or {}
        if resource_type:
            context['resource_type'] = resource_type
        if resource_id:
            context['resource_id'] = resource_id
            
        super().__init__(
            message,
            status_code=404,
            error_code="TWITTER_NOT_FOUND_ERROR",
            context=context,
            original_exception=original_exception
        )

class TwitterValidationError(TwitterMCPError):
    """Exception for input validation errors."""
    
    def __init__(
        self, 
        message: str,
        field_name: Optional[str] = None,
        field_value: Optional[Any] = None,
        context: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None
    ):
        context = context or {}
        if field_name:
            context['field_name'] = field_name
        if field_value is not None:
            context['field_value'] = str(field_value)
            
        super().__init__(
            message,
            error_code="TWITTER_VALIDATION_ERROR",
            context=context,
            original_exception=original_exception
        )

class TwitterConfigurationError(TwitterMCPError):
    """Exception for configuration-related errors."""
    
    def __init__(
        self, 
        message: str,
        config_key: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None
    ):
        context = context or {}
        if config_key:
            context['config_key'] = config_key
            
        super().__init__(
            message,
            error_code="TWITTER_CONFIG_ERROR",
            context=context,
            original_exception=original_exception
        )

class TwitterMediaUploadError(TwitterMCPError):
    """Exception for media upload related errors."""
    
    def __init__(
        self, 
        message: str,
        media_size: Optional[int] = None,
        media_type: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None
    ):
        context = context or {}
        if media_size:
            context['media_size_bytes'] = media_size
        if media_type:
            context['media_type'] = media_type
            
        super().__init__(
            message,
            error_code="TWITTER_MEDIA_UPLOAD_ERROR",
            context=context,
            original_exception=original_exception
        )

class TwitterClientError(TwitterMCPError):
    """Exception for Twitter client initialization or connection errors."""
    
    def __init__(
        self, 
        message: str,
        context: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None
    ):
        super().__init__(
            message,
            error_code="TWITTER_CLIENT_ERROR",
            context=context,
            original_exception=original_exception
        )

# Error mapping functions for converting external exceptions
def map_tweepy_error(exception: Exception, context: Optional[Dict[str, Any]] = None) -> TwitterMCPError:
    """Map Tweepy exceptions to our custom error hierarchy."""
    from tweepy.errors import TweepyException
    
    if not isinstance(exception, TweepyException):
        return TwitterMCPError(
            f"Unexpected error: {str(exception)}",
            context=context,
            original_exception=exception
        )
    
    response = getattr(exception, 'response', None)
    status_code = response.status_code if response else None
    
    message = str(exception)
    
    # Map based on status code
    if status_code == 401:
        return TwitterAuthenticationError(
            message=message,
            context=context,
            original_exception=exception
        )
    elif status_code == 403:
        return TwitterForbiddenError(
            message=message,
            context=context,
            original_exception=exception
        )
    elif status_code == 404:
        return TwitterNotFoundError(
            message=message,
            context=context,
            original_exception=exception
        )
    elif status_code == 429:
        # Try to extract retry-after header
        retry_after = None
        if response and hasattr(response, 'headers'):
            retry_after = response.headers.get('retry-after')
            if retry_after:
                try:
                    retry_after = int(retry_after)
                except ValueError:
                    retry_after = None
                    
        return TwitterRateLimitError(
            message=message,
            retry_after=retry_after,
            context=context,
            original_exception=exception
        )
    else:
        return TwitterAPIError(
            message=message,
            status_code=status_code,
            context=context,
            original_exception=exception
        )

def map_aiohttp_error(exception: Exception, context: Optional[Dict[str, Any]] = None) -> TwitterMCPError:
    """Map aiohttp exceptions to our custom error hierarchy."""
    import aiohttp
    
    message = str(exception)
    
    if isinstance(exception, aiohttp.ClientTimeout):
        return TwitterAPIError(
            f"Request timeout: {message}",
            error_code="TWITTER_TIMEOUT_ERROR",
            context=context,
            original_exception=exception
        )
    elif isinstance(exception, aiohttp.ClientConnectionError):
        return TwitterClientError(
            f"Connection error: {message}",
            context=context,
            original_exception=exception
        )
    else:
        return TwitterAPIError(
            f"HTTP client error: {message}",
            context=context,
            original_exception=exception
        )