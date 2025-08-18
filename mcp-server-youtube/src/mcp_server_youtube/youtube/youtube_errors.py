class YouTubeClientError(Exception):
    """Base exception for YouTube client errors."""
    def __init__(self, message: str, code: str = "YOUTUBE_CLIENT_ERROR", status_code: int = 500):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)


class YouTubeApiError(YouTubeClientError):
    """Exception for YouTube API errors."""
    def __init__(self, message: str = "YouTube API error occurred"):
        super().__init__(message, code="YOUTUBE_API_ERROR", status_code=502)


class YouTubeTranscriptError(YouTubeClientError):
    """Exception for transcript retrieval errors."""
    def __init__(self, message: str = "Transcript retrieval failed"):
        super().__init__(message, code="YOUTUBE_TRANSCRIPT_ERROR", status_code=503)


class ServiceUnavailableError(YouTubeClientError):
    """Exception for when YouTube services are unavailable."""
    def __init__(self, message: str = "YouTube service is unavailable"):
        super().__init__(message, code="SERVICE_UNAVAILABLE", status_code=503)


class InvalidResponseError(YouTubeClientError):
    """Exception for invalid responses from YouTube API."""
    def __init__(self, message: str = "Invalid response from YouTube API"):
        super().__init__(message, code="INVALID_YOUTUBE_RESPONSE", status_code=502)


class QuotaExceededError(YouTubeClientError):
    """Exception for YouTube API quota exceeded."""
    def __init__(self, message: str = "YouTube API quota exceeded"):
        super().__init__(message, code="QUOTA_EXCEEDED", status_code=429)


class ValidationError(YouTubeClientError):
    """Exception for input validation failures."""
    def __init__(self, message: str = "Input validation failed"):
        super().__init__(message, code="VALIDATION_ERROR", status_code=400)


class VideoNotFoundError(YouTubeClientError):
    """Exception for when a video is not found or unavailable."""
    def __init__(self, message: str = "Video not found or unavailable"):
        super().__init__(message, code="VIDEO_NOT_FOUND", status_code=404)


class TranscriptNotAvailableError(YouTubeClientError):
    """Exception for when transcripts are not available for a video."""
    def __init__(self, message: str = "Transcript not available for this video"):
        super().__init__(message, code="TRANSCRIPT_NOT_AVAILABLE", status_code=404)