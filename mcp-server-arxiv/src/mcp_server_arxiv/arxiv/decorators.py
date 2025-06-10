import time
import logging
from functools import wraps
from typing import Callable, Type

logger = logging.getLogger(__name__)


class RetryLimitExceeded(Exception):
    """
    Raised when all retry attempts for a given operation fail.
    Captures the original exception for downstream handling.
    """

    def __init__(self, operation: str, last_exception: Exception):
        message = (
            f"Retry limit exceeded for operation '{operation}': "
            f"{type(last_exception).__name__} - {last_exception}"
        )
        super().__init__(message)
        self.last_exception = last_exception


def retry_on_exception(
    retries: int = 3,
    delay: float = 2.0,
    backoff: float = 2.0,
    exceptions: tuple[Type[Exception], ...] = (Exception,),
    operation: str = "operation"
) -> Callable:
    """
    Decorator for retrying a synchronous function call upon exceptions.
    
    Retries the function up to `retries` times, using exponential backoff starting
    with `delay` seconds and multiplying each retry delay by `backoff`.

    Logs each retry attempt with WARNING level and the final failure with ERROR level.

    Args:
        retries: Number of retry attempts before giving up.
        delay: Initial wait time before retrying, in seconds.
        backoff: Multiplier for exponential backoff.
        exceptions: Tuple of exception classes to catch and retry upon.
        operation: String description of the operation for logging context.

    Returns:
        The result of the function if successful.

    Raises:
        RetryLimitExceeded: After exhausting retries without success.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 0
            wait = delay

            while attempt < retries:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    attempt += 1
                    if attempt < retries:
                        logger.warning(
                            f"[Retry {attempt}/{retries}] for {operation} due to {type(e).__name__}: {e}. "
                            f"Retrying in {wait:.1f} seconds..."
                        )
                        time.sleep(wait)
                        wait *= backoff
                    else:
                        logger.error(
                            f"[Final Failure] {operation} failed after {retries} attempts "
                            f"due to: {type(e).__name__} - {e}",
                            exc_info=True
                        )
                        raise RetryLimitExceeded(operation, e) from e

        return wrapper

    return decorator
