from typing import Any
import logging

logger = logging.getLogger(__name__)

class TwitterMCPError(Exception):
    """Base exception for all Twitter MCP server errors."""
    
    def __init__(
        self, 
        message: str, 
        error_code: str = "TWITTER_MCP_ERROR",
        context: dict[str, Any] | None = None,
        original_exception: Exception | None = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.context = context or {}
        self.original_exception = original_exception

class TwitterAPIError(TwitterMCPError):
    """Exception for Twitter API related errors."""
    
    def __init__(
        self, 
        message: str, 
        status_code: int | None = None,
        error_code: str = "TWITTER_API_ERROR",
        context: dict[str, Any] | None = None,
        original_exception: Exception | None = None
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
        context: dict[str, Any] | None = None,
        original_exception: Exception | None = None
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
        retry_after: int | None = None,
        context: dict[str, Any] | None = None,
        original_exception: Exception | None = None
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
        context: dict[str, Any] | None = None,
        original_exception: Exception | None = None
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
        resource_type: str | None = None,
        resource_id: str | None = None,
        context: dict[str, Any] | None = None,
        original_exception: Exception | None = None
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
        field_name: str | None = None,
        field_value: Any | None = None,
        context: dict[str, Any] | None = None,
        original_exception: Exception | None = None
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
        config_key: str | None = None,
        context: dict[str, Any] | None = None,
        original_exception: Exception | None = None
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
        media_size: int | None = None,
        media_type: str | None = None,
        context: dict[str, Any] | None = None,
        original_exception: Exception | None = None
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
        context: dict[str, Any] | None = None,
        original_exception: Exception | None = None
    ):
        super().__init__(
            message,
            error_code="TWITTER_CLIENT_ERROR",
            context=context,
            original_exception=original_exception
        )

def create_final_retry_exception(retry_state, base_exception_class=TwitterAPIError):
    """Create a descriptive exception after all retry attempts are exhausted."""
    
    attempt_number = retry_state.attempt_number
    outcome = retry_state.outcome
    operation_name = getattr(retry_state.fn, '__name__', 'unknown_operation')
    
    # Get the original exception
    original_exception = None
    if outcome and outcome.failed:
        original_exception = outcome.exception()
    
    # Create detailed error message
    error_message = (
        f"Operation '{operation_name}' failed after {attempt_number} attempts. "
        f"Final error: {str(original_exception)}"
    )
    
    # Create context for the exception
    context = {
        'operation': operation_name,
        'total_attempts': attempt_number,
        'final_error_type': type(original_exception).__name__ if original_exception else 'Unknown',
        'elapsed_time_seconds': getattr(retry_state, 'seconds_since_start', None)
    }
    
    # Return appropriately typed exception
    return base_exception_class(
        message=error_message,
        context=context,
        original_exception=original_exception
    )

def on_final_retry_failure(retry_state):
    """Called when all retry attempts are exhausted - logs final failure."""
    operation_name = getattr(retry_state.fn, '__name__', 'unknown_operation')
    
    # Get the original exception for context
    original_exception = None
    if retry_state.outcome and retry_state.outcome.failed:
        original_exception = retry_state.outcome.exception()
    
    logger.error(
        f"All retry attempts exhausted for {operation_name}",
        extra={
            'operation': operation_name,
            'total_attempts': retry_state.attempt_number,
            'total_elapsed_time': getattr(retry_state, 'seconds_since_start', None),
            'final_exception_type': type(original_exception).__name__ if original_exception else 'Unknown',
            'final_error_message': str(original_exception) if original_exception else 'Unknown error'
        }
    )
    
    # Create and raise the final descriptive exception
    final_exception = create_final_retry_exception(retry_state, TwitterAPIError)
    raise final_exception

def map_tweepy_error(exception: Exception, context: dict[str, Any] | None = None) -> TwitterMCPError:
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

def map_aiohttp_error(exception: Exception, context: dict[str, Any] | None = None) -> TwitterMCPError:
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