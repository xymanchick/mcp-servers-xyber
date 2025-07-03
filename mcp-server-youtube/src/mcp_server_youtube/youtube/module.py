import json
import logging
import xml
from datetime import datetime
from functools import lru_cache
from typing import Any, Optional, Dict, List, Tuple
import xml.etree.ElementTree as ET

# --- Third-party Imports ---
from googleapiclient.discovery import Resource, build
from googleapiclient.errors import HttpError
from mcp_server_youtube.youtube.config import YouTubeConfig
from mcp_server_youtube.youtube.youtube_errors import (YouTubeApiError,
                                                       YouTubeClientError,
                                                       YouTubeTranscriptError)
from mcp_server_youtube.utils.data_utils import DataUtils
from mcp_server_youtube.youtube.models import YouTubeVideo
import requests

from youtube_transcript_api import (
    NoTranscriptFound,
    TranscriptsDisabled,
    CouldNotRetrieveTranscript,
    YouTubeTranscriptApi,
    VideoUnavailable
)

# --- Setup Logger ---
logger = logging.getLogger(__name__)


# --- YouTubeSearcher Class ---
class YouTubeSearcher:
    """
    Searches YouTube for videos based on a query and fetches their transcripts.

    Handles interaction with the YouTube Data API v3 and YouTube Transcript API.
    """

    def __init__(self, config: YouTubeConfig):
        """
        Initializes the YouTubeSearcher.

        Args:
            config: The YouTube configuration settings

        Raises:
            YouTubeClientError: If the API service initialization fails.
        """
        self.config = config
        self.youtube_service: Resource = self._initialize_yt_service()
        self.max_transcript_preview = 500

    def _initialize_yt_service(self) -> Resource:
        """
        Initialize the YouTube Data API service.

        Returns:
            The initialized YouTube Data API service.

        Raises:
            YouTubeClientError: If the API service initialization fails.
        """
        try:
            # Build the YouTube Data API service object
            service = build("youtube", "v3", developerKey=self.config.api_key)
            logger.debug("YouTube Data API service initialized successfully.")
            return service
        except Exception as e:
            msg = f"Failed to initialize YouTube Data API service: {e}"
            logger.exception(msg)
            raise YouTubeClientError(msg) from e

    def _build_search_params(
            self,
            query: str,
            max_results: int = 15,
            order_by: Optional[str] = None,
            published_after: Optional[str] = None,
            published_before: Optional[str] = None
    ) -> dict:
        """
        Build search parameters for YouTube Data API request.

        Args:
            query: Search query string
            max_results: Maximum number of results to return
            order_by: Sort order for results (relevance, date, viewCount, rating)
            published_after: Only include videos published after this date (datetime or str)
            published_before: Only include videos published before this date (datetime or str)

        Returns:
            Dictionary of search parameters
        """
        # Base search parameters
        search_params = {
            'q': query,
            'part': 'id,snippet',
            'maxResults': max_results,
            'type': 'video',
            'order': order_by or 'relevance'
        }

        # Convert datetime objects to ISO format strings if necessary
        if isinstance(published_after, datetime):
            published_after = published_after.isoformat()
        if isinstance(published_before, datetime):
            published_before = published_before.isoformat()

        # Add date filters if provided
        if published_after:
            search_params['publishedAfter'] = DataUtils.format_iso_datetime(
                published_after, for_youtube_api=True
            )
        if published_before:
            search_params['publishedBefore'] = DataUtils.format_iso_datetime(
                published_before, for_youtube_api=True
            )

        return search_params

    def _is_valid_search_item(self, search_item: dict) -> bool:
        """
        Check if a search item is valid and represents a YouTube video.

        Args:
            search_item: A search result item from YouTube Data API.

        Returns:
            True if the item is a valid YouTube video, False otherwise.
        """
        return search_item.get("id", {}).get("kind") == "youtube#video"

    def _create_video_from_search_item(self, search_item: dict, transcript: str,
                                       transcript_language: str) -> YouTubeVideo:
        """
        Create a YouTubeVideo object from a search item and transcript.

        Args:
            search_item: A search result item from YouTube Data API.
            transcript: The video's transcript text.
            transcript_language: The language of the transcript.

        Returns:
            A YouTubeVideo object containing video details and transcript.
        """
        snippet = search_item.get("snippet", {})
        return YouTubeVideo(
            video_id=search_item.get("id", {}).get("videoId", "N/A"),
            title=snippet.get("title", "N/A"),
            description=snippet.get("description", ""),
            channel=snippet.get("channelTitle", "N/A"),
            published_at=snippet.get("publishedAt", "N/A"),
            thumbnail=snippet.get("thumbnails", {}).get("default", {}).get("url", "N/A"),
            transcript=transcript,
            transcript_language=transcript_language,
            has_transcript=transcript is not None
        )

    def _get_transcript_by_id(self, video_id: str, language: str = 'en') -> Tuple[Optional[str], Optional[str]]:
        """
        Get transcript for a video ID - uses any available transcript
        Returns: (transcript_entries, language_code) or (None, None)
        """
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

            # First try to get English transcript if available
            try:
                transcript = transcript_list.find_transcript(['en'])
                transcript_entries = transcript.fetch()
                logger.info(f"Found English transcript for video {video_id}")

                # Convert transcript entries to text
                transcript_text_parts = []
                for entry in transcript_entries:
                    if hasattr(entry, 'text'):
                        transcript_text_parts.append(entry.text)
                    elif isinstance(entry, dict) and 'text' in entry:
                        transcript_text_parts.append(entry['text'])
                    else:
                        transcript_text_parts.append(str(entry))

                transcript_text = " ".join(transcript_text_parts)

                # Truncate if too long
                if len(transcript_text) > self.max_transcript_preview:
                    transcript_text = transcript_text[:self.max_transcript_preview] + "..."

                return transcript_text, 'en'
            except NoTranscriptFound:
                logger.debug(f"No English transcript for video {video_id}, trying other languages")

            # If no English, get any available transcript
            available_transcripts = list(transcript_list)
            if not available_transcripts:
                logger.warning(f"No transcripts available for video {video_id}")
                return None, None

            # Try each available transcript until one works
            for transcript in available_transcripts:
                try:
                    transcript_entries = transcript.fetch()
                    language_code = transcript.language_code
                    logger.info(f"Found transcript in {language_code} for video {video_id}")

                    # Convert transcript entries to text
                    transcript_text_parts = []
                    for entry in transcript_entries:
                        if hasattr(entry, 'text'):
                            transcript_text_parts.append(entry.text)
                        elif isinstance(entry, dict) and 'text' in entry:
                            transcript_text_parts.append(entry['text'])
                        else:
                            transcript_text_parts.append(str(entry))

                    transcript_text = " ".join(transcript_text_parts)

                    # Truncate if too long
                    if len(transcript_text) > self.max_transcript_preview:
                        transcript_text = transcript_text[:self.max_transcript_preview] + "..."

                    return transcript_text, language_code
                except Exception as fetch_error:
                    logger.debug(f"Failed to fetch {transcript.language_code} transcript for {video_id}: {fetch_error}")
                    continue

            # If we get here, no transcripts worked
            logger.warning(f"No working transcripts found for video {video_id}")
            return None, None

        except TranscriptsDisabled:
            logger.warning(f"Transcripts disabled for video {video_id}")
            return None, None
        except VideoUnavailable:
            logger.warning(f"Video {video_id} is unavailable")
            return None, None
        except Exception as e:
            logger.error(f"Unexpected error getting transcript for {video_id}: {str(e)}")
            return None, None

    def search_videos(
            self,
            query: str,
            max_results: int = 15,
            language: str = 'en',
            order_by: str = 'relevance',
            published_after: Optional[datetime] = None,
            published_before: Optional[datetime] = None
    ) -> List[YouTubeVideo]:
        """
        Search YouTube videos and retrieve their transcripts.

        Args:
            query: Search query string
            max_results: Maximum number of results to return (1-50)
            language: Preferred language for transcripts (default: 'en')
            order_by: Sort order ('relevance', 'date', 'viewCount', 'rating')
            published_after: Only return videos published after this date
            published_before: Only return videos published before this date

        Returns:
            A list of YouTubeVideo objects with video details and transcripts.

        Raises:
            YouTubeApiError: If a YouTube Data API error occurs.
            YouTubeClientError: For other unexpected errors during the search.
        """
        try:
            logger.info(f"Searching YouTube for query: '{query}' with max_results={max_results}")

            # Build search parameters
            search_params = self._build_search_params(
                query=query,
                max_results=max_results,
                order_by=order_by,
                published_after=published_after,
                published_before=published_before
            )

            # Execute search
            search_response = self.youtube_service.search().list(**search_params).execute()

            # Process search results
            videos = []
            items = search_response.get('items', [])

            for item in items:
                if not self._is_valid_search_item(item):
                    continue

                video_id = item.get('id', {}).get('videoId')
                if not video_id:
                    logger.warning(f"Search item found without videoId: {item}")
                    continue

                # Fetch transcript and language
                transcript, transcript_language = self._get_transcript_by_id(video_id, language)

                # Create YouTubeVideo object
                video = self._create_video_from_search_item(item, transcript, transcript_language)
                videos.append(video)

            # Log results
            videos_with_transcripts = len([v for v in videos if v.has_transcript])
            logger.info(f"Found {len(videos)} videos, {videos_with_transcripts} with transcripts")

            return videos

        except HttpError as e:
            error_msg = f"YouTube API error: {e}"
            logger.error(error_msg, exc_info=True)
            raise YouTubeApiError(error_msg) from e
        except Exception as e:
            # Catch-all for other unexpected errors during search/transcript process
            msg = f"An unexpected error occurred during YouTube search: {e}"
            logger.error(msg, exc_info=True)
            raise YouTubeClientError(msg) from e


@lru_cache(maxsize=1)
def get_youtube_searcher() -> YouTubeSearcher:
    """Get a cached instance of YouTubeSearcher."""
    config = YouTubeConfig()
    searcher = YouTubeSearcher(config)
    return searcher