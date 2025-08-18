class YouTubeClientError(Exception):
    """Base exception for YouTube client errors."""

    pass


class YouTubeApiError(YouTubeClientError):
    """Exception for YouTube API errors."""

    pass


class YouTubeTranscriptError(YouTubeClientError):
    """Exception for transcript retrieval errors."""

    pass
