class LurkyError(Exception):
    """Base exception for Lurky service."""

    pass


class LurkyAPIError(LurkyError):
    """Raised when the Lurky API returns an error."""

    def __init__(self, message: str, status_code: int | None = None, response_text: str | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text


class LurkyAuthError(LurkyAPIError):
    """Raised when there's an authentication error with the Lurky API."""

    pass


class LurkyNotFoundError(LurkyAPIError):
    """Raised when a requested resource is not found."""

    pass
