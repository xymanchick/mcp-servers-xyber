# exceptions.py [Hierarchy of Errors] --> Created and Modified by Ansh Juneja ....

class BaseMCPException(Exception):
    """Base class for MCP-related exceptions."""

class ServiceUnavailableError(BaseMCPException):
    """Indicates downstream service is unavailable."""

class InvalidResponseError(BaseMCPException):
    """Indicates downstream service returned invalid or unexpected response."""

class InputValidationError(BaseMCPException):
    """Invalid input from user."""

class UnknownMCPError(BaseMCPException):
    """Catch-all for unknown errors."""

