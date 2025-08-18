"""
Utility to monkey-patch tenacity for faster tests.
"""
import tenacity

# Store original retry function
_original_retry = tenacity.retry

def no_retry_decorator(*args, **kwargs):
    """Decorator that returns the function unchanged (no retry behavior)."""
    def decorator(func):
        return func
    return decorator

def disable_tenacity_retry():
    """Replace tenacity.retry with a no-op decorator."""
    tenacity.retry = no_retry_decorator

def restore_tenacity_retry():
    """Restore original tenacity.retry."""
    tenacity.retry = _original_retry
