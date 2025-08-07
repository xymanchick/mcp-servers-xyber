"""YouTube searcher module with modern Python 3.10+ features."""
from __future__ import annotations

import logging
from datetime import datetime
from functools import lru_cache

from googleapiclient.discovery import build
from googleapiclient.discovery import Resource
from googleapiclient.errors import HttpError
from mcp_server_youtube.utils.data_utils import DataUtils
from mcp_server_youtube.youtube.config import get_youtube_config
from mcp_server_youtube.youtube.config import YouTubeConfig
from mcp_server_youtube.youtube.models import TranscriptStatus
from mcp_server_youtube.youtube.models import YouTubeVideo
from mcp_server_youtube.youtube.transcript import TranscriptFetcher
from mcp_server_youtube.youtube.youtube_errors import (
    YouTubeApiError,
    YouTubeClientError,
    ServiceUnavailableError,
    InvalidResponseError,
    QuotaExceededError,
)
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

logger = logging.getLogger(__name__)


# --- Setup Retry Decorators ---
retry_search = retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=0.5, max=10),   
    retry=retry_if_exception_type((YouTubeClientError, YouTubeApiError)),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)

retry_fetch_transcript = retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=5),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
    retry_error_callback=lambda retry_state: ('Transcript service temporarily unavailable', None, False)
)

# --- YouTubeSearcher Class ---
@lru_cache(maxsize=1)
def get_youtube_searcher() -> YouTubeSearcher:
    """Get a cached instance of YouTubeSearcher."""
    config = get_youtube_config()
    return YouTubeSearcher(config)


class YouTubeSearcher:
    """YouTube video searcher with transcript fetching capabilities.

    Handles interaction with the YouTube Data API v3 and YouTube Transcript API.
    """

    def __init__(self, config: YouTubeConfig) -> None:
        """Initialize the YouTubeSearcher.

        Args:
            config: The YouTube configuration settings

        Raises:
            YouTubeClientError: If the API service initialization fails.

        """
        self.config = config
        self.youtube_service: Resource = self._initialize_yt_service()
        self.max_transcript_preview = 500

    def _initialize_yt_service(self) -> Resource:
        """Initialize the YouTube Data API service.

        Returns:
            The initialized YouTube Data API service.

        Raises:
            YouTubeClientError: If the API service initialization fails.

        """
        try:
            logger.debug(f'Initializing YouTube Data API v3 service with API key: {"✓ Present" if self.config.api_key else "✗ Missing"}')
            service = build('youtube', 'v3', developerKey=self.config.api_key)
            logger.debug('YouTube Data API service initialized successfully.')
            return service
        except Exception as e:
            logger.error(f'Failed to initialize YouTube Data API service: {str(e)}', exc_info=True)
            raise YouTubeClientError(f'Failed to initialize YouTube service: {e}') from e

    def _build_search_params(
            self,
            query: str,
            max_results: int = 15,
            order_by: str | None = None,
            published_after: str | None = None,
            published_before: str | None = None,
    ) -> dict[str, str | int]:
        """Build search parameters for YouTube Data API request.

        Args:
            query: Search query string
            max_results: Maximum number of results to return
            order_by: Sort order for results (relevance, date, viewCount, rating)
            published_after: Only include videos published after this date (ISO format)
            published_before: Only include videos published before this date (ISO format)

        Returns:
            Dictionary of search parameters
        """
        search_params = {
            'q': query,
            'part': 'id,snippet',
            'maxResults': max_results,
            'type': 'video',
            'order': order_by or 'relevance',
        }

        # Add date filters if provided
        if published_after:
            search_params['publishedAfter'] = published_after
            logger.debug(f'Applied publishedAfter filter: {published_after}')
        if published_before:
            search_params['publishedBefore'] = published_before
            logger.debug(f'Applied publishedBefore filter: {published_before}')

        logger.debug(f'Built search parameters: {search_params}')
        return search_params

    def _is_valid_search_item(self, search_item: dict) -> bool:
        """Check if a search item is valid and represents a YouTube video.

        Args:
            search_item: A search result item from YouTube Data API.

        Returns:
            True if the item is a valid YouTube video, False otherwise.
        """
        return search_item.get('id', {}).get('kind') == 'youtube#video'

    @lru_cache(maxsize=128)
    @retry_fetch_transcript
    def _get_transcript_by_id(
            self, video_id: str, language: str = 'en'
    ) -> tuple[str | None, str | None, bool]:
        """Get transcript for a video ID using TranscriptFetcher.

        Args:
            video_id: YouTube video ID
            language: Preferred language code

        Returns:
            Tuple of (transcript_text_or_status, language_code, has_transcript)
        """
        logger.debug(f'Attempting to fetch transcript for video {video_id}')

        # Use TranscriptFetcher for better handling
        fetcher = TranscriptFetcher(video_id)
        result = fetcher.fetch(language)

        if result.status == TranscriptStatus.SUCCESS:
            return result.transcript, result.language, True

        # Create user-friendly status message
        status_message = 'Transcript unavailable'
        if result.available_languages:
            langs = ', '.join(result.available_languages)
            status_message = f'Available languages: {langs}'

        if result.error_message:
            status_message += f'\nError: {result.error_message}'

        return status_message, result.language if result.language else None, False

    def _create_video_from_search_item(
            self,
            search_item: dict,
            transcript: str | None,
            transcript_language: str | None,
            has_transcript: bool,
    ) -> YouTubeVideo:
        """Create a YouTubeVideo object from a search item and transcript.

        Args:
            search_item: A search result item from YouTube Data API
            transcript: The video's transcript text or status message
            transcript_language: The language of the transcript
            has_transcript: Whether the video has a real transcript

        Returns:
            A YouTubeVideo object containing video details and transcript
        """
        snippet = search_item.get('snippet', {})

        return YouTubeVideo(
            video_id=search_item.get('id', {}).get('videoId', 'N/A'),
            title=snippet.get('title', 'N/A'),
            description=snippet.get('description', ''),
            channel=snippet.get('channelTitle', 'N/A'),
            published_at=snippet.get('publishedAt', 'N/A'),
            thumbnail=snippet.get('thumbnails', {}).get('default', {}).get('url', 'N/A'),
            transcript=transcript,
            transcript_language=transcript_language,
            has_transcript=has_transcript,
        )

    @retry_search
    def search_videos(
            self,
            query: str,
            max_results: int = 15,
            language: str = 'en',
            order_by: str = 'relevance',
            published_after: datetime | None = None,
            published_before: datetime | None = None,
    ) -> list[YouTubeVideo]:
        """Search YouTube videos and retrieve their transcripts.

        Args:
            query: Search query string
            max_results: Maximum number of results to return (1-50)
            language: Preferred language for transcripts
            order_by: Sort order ('relevance', 'date', 'viewCount', 'rating')
            published_after: Only return videos published after this date
            published_before: Only return videos published before this date

        Returns:
            A list of YouTubeVideo objects with video details and transcripts

        Raises:
            YouTubeApiError: If a YouTube Data API error occurs
            YouTubeClientError: For other unexpected errors during the search
        """
        try:
            logger.info(f"Searching YouTube for query: '{query}' with max_results={max_results}")
            logger.debug(f"Search parameters: language={language}, order_by={order_by}")
            
            search_params = self._build_search_params(
                query,
                max_results,
                order_by=order_by,
                published_after=DataUtils.format_iso_datetime(published_after) if published_after else None,
                published_before=DataUtils.format_iso_datetime(published_before) if published_before else None,
            )

            logger.debug(f"Executing YouTube API search with parameters: {search_params}")
            search_response = self.youtube_service.search().list(**search_params).execute()
            items = search_response.get('items', [])
            logger.debug(f"YouTube API returned {len(items)} search results")

            videos = []
            for item in items:
                if not self._is_valid_search_item(item):
                    logger.debug(f"Skipping invalid search item: {item.get('id', {}).get('kind', 'unknown')}")
                    continue

                video_id = item.get('id', {}).get('videoId')
                if not video_id:
                    logger.warning(f'Search item found without videoId: {item}')
                    continue

                logger.debug(f"Processing video: {video_id}")

                # Fetch transcript and language
                transcript, transcript_language, has_transcript = self._get_transcript_by_id(
                    video_id, language
                )

                if has_transcript:
                    logger.debug(f"Transcript fetched successfully for video {video_id} in language {transcript_language}")
                else:
                    logger.debug(f"Transcript not available for video {video_id}: {transcript}")

                # Create YouTubeVideo object
                video = self._create_video_from_search_item(
                    item, transcript, transcript_language, has_transcript
                )
                videos.append(video)

            videos_with_transcripts = len([v for v in videos if v.has_transcript])
            logger.info(f'Search completed successfully: {len(videos)} videos found, {videos_with_transcripts} with transcripts')
            
            if videos_with_transcripts == 0:
                logger.warning(f"No transcripts were available for query '{query}' in language '{language}'")

            return videos

        except (HttpError) as e:
            logger.error(f"YouTube API error: {e}", exc_info=True)
            logger.debug(f"API error details: status={e.resp.status}, reason={e.resp.reason}")
            
            # Handle specific HTTP error codes with appropriate exceptions
            if e.resp.status == 403:
                if 'quotaExceeded' in str(e) or 'quota' in str(e).lower():
                    raise QuotaExceededError(f"YouTube API quota exceeded: {e.resp.reason}")
                else:
                    raise YouTubeApiError(f"YouTube API access forbidden: {e.resp.reason}")
            elif e.resp.status == 400:
                raise InvalidResponseError(f"Invalid request to YouTube API: {e.resp.reason}")
            elif e.resp.status >= 500:
                raise ServiceUnavailableError(f"YouTube API service unavailable: {e.resp.reason}")
            else:
                raise YouTubeApiError(f"YouTube API error ({e.resp.status}): {e.resp.reason}")
        
        except Exception as e:
            msg = f'An unexpected error occurred during YouTube search: {e}'
            logger.error(msg, exc_info=True)
            logger.debug(f"Error type: {type(e).__name__}, Query: '{query}'")
            raise ServiceUnavailableError(msg) from e
