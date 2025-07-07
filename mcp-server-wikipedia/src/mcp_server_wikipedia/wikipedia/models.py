class WikipediaServiceError(Exception):
    """Base exception for Wikipedia client errors."""

    pass


class WikipediaConfigError(WikipediaServiceError):
    """Configuration-related errors for the Wikipedia client."""

    pass


class WikipediaAPIError(WikipediaServiceError):
    """Exception for errors during Wikipedia API calls."""

    pass


class ArticleNotFoundError(WikipediaAPIError):
    """Raised when a specific Wikipedia article cannot be found."""

    def __init__(self, title: str):
        super().__init__(f"Article with title '{title}' not found.")
        self.title = title
