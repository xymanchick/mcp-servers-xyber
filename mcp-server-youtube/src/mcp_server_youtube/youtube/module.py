from __future__ import annotations

import logging
import xml
from datetime import datetime
from functools import lru_cache

from googleapiclient.discovery import build
from googleapiclient.discovery import Resource
from googleapiclient.errors import HttpError
from mcp_server_youtube.utils.data_utils import DataUtils
from mcp_server_youtube.youtube.config import YouTubeConfig
from mcp_server_youtube.youtube.models import YouTubeVideo
from mcp_server_youtube.youtube.youtube_errors import YouTubeApiError
from mcp_server_youtube.youtube.youtube_errors import YouTubeClientError
from youtube_transcript_api import NoTranscriptFound
from youtube_transcript_api import TranscriptsDisabled
from youtube_transcript_api import VideoUnavailable
from youtube_transcript_api import YouTubeTranscriptApi


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
            service = build('youtube', 'v3', developerKey=self.config.api_key)
            logger.debug('YouTube Data API service initialized successfully.')
            return service
        except Exception as e:
            msg = f'Failed to initialize YouTube Data API service: {e}'
            logger.exception(msg)
            raise YouTubeClientError(msg) from e

    def _build_search_params(
            self,
            query: str,
            max_results: int = 15,
            order_by: str | None = None,
            published_after: str | None = None,
            published_before: str | None = None
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
        return search_item.get('id', {}).get('kind') == 'youtube#video'

    def _create_video_from_search_item(self, search_item: dict, transcript: str | None, transcript_language: str | None) -> YouTubeVideo:
        """
        Create a YouTubeVideo object from a search item and transcript.

        Args:
            search_item: A search result item from YouTube Data API.
            transcript: The video's transcript text or status message.
            transcript_language: The language of the transcript.

        Returns:
            A YouTubeVideo object containing video details and transcript.
        """
        snippet = search_item.get('snippet', {})

        # Determine if we have a real transcript or just a status message
        has_real_transcript = False
        if transcript is not None:
            # Check if it's a real transcript (not a status message)
            status_indicators = [
                'Transcript available in',
                'Transcripts disabled',
                'Video unavailable',
                'Error accessing transcript',
                'No transcripts found',
                'currently blocked by YouTube'
            ]

            has_real_transcript = not any(indicator in transcript for indicator in status_indicators)

        return YouTubeVideo(
            video_id=search_item.get('id', {}).get('videoId', 'N/A'),
            title=snippet.get('title', 'N/A'),
            description=snippet.get('description', ''),
            channel=snippet.get('channelTitle', 'N/A'),
            published_at=snippet.get('publishedAt', 'N/A'),
            thumbnail=snippet.get('thumbnails', {}).get('default', {}).get('url', 'N/A'),
            transcript=transcript,
            transcript_language=transcript_language,
            has_transcript=has_real_transcript
        )

    def _get_transcript_by_id(self, video_id: str, language: str = 'en') -> tuple[str | None, str | None]:
        """
        Get transcript for a video ID with helpful status messages
        Returns: (transcript_text_or_status, language_code)
        """
        try:
            logger.debug(f'Attempting to fetch transcript for video {video_id}')

            # Get transcript list with error handling
            try:
                transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
                logger.debug(f'Successfully got transcript list for video {video_id}')
            except TranscriptsDisabled:
                logger.warning(f'Transcripts disabled for video {video_id}')
                return 'Transcripts disabled by video creator', None
            except VideoUnavailable:
                logger.warning(f'Video {video_id} is unavailable')
                return 'Video unavailable', None
            except Exception as e:
                logger.error(f'Error getting transcript list for video {video_id}: {str(e)}')
                return f'Error accessing transcript: {str(e)}', None

            # Try to get transcript in preferred language
            try:
                transcript = transcript_list.find_transcript([language])
                logger.info(f'Found transcript in {language} for video {video_id}')
                language_code = language
            except NoTranscriptFound:
                # If preferred language not found, try English
                try:
                    transcript = transcript_list.find_transcript(['en'])
                    logger.info(f'Preferred language not found, using English transcript for video {video_id}')
                    language_code = 'en'
                except NoTranscriptFound:
                    # If English not found, try any available transcript
                    try:
                        available_transcripts = list(transcript_list)
                        if available_transcripts:
                            transcript = available_transcripts[0]
                            language_code = transcript.language_code
                            logger.info(f'Using available transcript in {language_code} for video {video_id}')
                        else:
                            raise NoTranscriptFound()
                    except NoTranscriptFound:
                        logger.warning(f'No working transcripts found for video {video_id}')
                        return 'No transcripts available', None

            # Fetch and process transcript with enhanced error handling
            try:
                # Get transcript entries
                transcript_entries = transcript.fetch()

                # Validate transcript entries
                if not transcript_entries or len(transcript_entries) == 0:
                    logger.warning(f'Empty transcript entries for video {video_id}')
                    return f'Transcript available in {language_code} but empty', language_code

                # Process transcript entries
                transcript_text_parts = []
                for entry in transcript_entries:
                    try:
                        # Try to get text from entry
                        if isinstance(entry, dict):
                            text = entry.get('text')
                        else:
                            text = getattr(entry, 'text', None)

                        if not text:
                            continue

                        # Clean and validate text
                        clean_text = str(text).strip()
                        if clean_text:
                            transcript_text_parts.append(clean_text)
                    except Exception as entry_error:
                        logger.debug(f'Error processing transcript entry: {str(entry_error)}')
                        continue

                # Validate final transcript
                transcript_text = '\n'.join(transcript_text_parts)
                if not transcript_text.strip():
                    logger.warning(f'Empty transcript text after processing for video {video_id}')
                    return f'Transcript available in {language_code} but empty', language_code

                logger.info(f'Successfully fetched transcript in {language_code} for video {video_id}')
                return transcript_text, language_code

            except (xml.etree.ElementTree.ParseError, xml.parsers.expat.ExpatError) as e:
                logger.warning(f'XML parsing error for video {video_id}: {str(e)}')
                return f"Transcript available in {language_code} but currently blocked by YouTube's anti-bot protection", language_code
            except Exception as e:
                if 'no element found' in str(e).lower():
                    logger.warning(f'Empty XML response for video {video_id}')
                    return f"Transcript available in {language_code} but currently blocked by YouTube's anti-bot protection", language_code
                logger.error(f'Error processing transcript for video {video_id}: {str(e)}', exc_info=True)
                return f'Error accessing transcript in {language_code}: {str(e)}', language_code

        except Exception as e:
            logger.error(f'Unexpected error in transcript fetching for video {video_id}: {str(e)}', exc_info=True)
            return f'Unexpected error: {str(e)}', None

    def search_videos(
        self,
        query: str,
        max_results: int = 15,
        language: str = 'en',
        order_by: str = 'relevance',
        published_after: datetime | None = None,
        published_before: datetime | None = None
    ) -> list[YouTubeVideo]:
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
                    logger.warning(f'Search item found without videoId: {item}')
                    continue

                # Fetch transcript and language
                transcript, transcript_language = self._get_transcript_by_id(video_id, language)

                # Create YouTubeVideo object
                video = self._create_video_from_search_item(item, transcript, transcript_language)
                videos.append(video)

            # Log results
            videos_with_transcripts = len([v for v in videos if v.has_transcript])
            logger.info(f'Found {len(videos)} videos, {videos_with_transcripts} with transcripts')

            return videos

        except HttpError as e:
            error_msg = f'YouTube API error: {e}'
            logger.error(error_msg, exc_info=True)
            raise YouTubeApiError(error_msg) from e
        except Exception as e:
            # Catch-all for other unexpected errors during search/transcript process
            msg = f'An unexpected error occurred during YouTube search: {e}'
            logger.error(msg, exc_info=True)
            raise YouTubeClientError(msg) from e


@lru_cache(maxsize=1)
def get_youtube_searcher() -> YouTubeSearcher:
    """Get a cached instance of YouTubeSearcher."""
    config = YouTubeConfig()
    searcher = YouTubeSearcher(config)
    return searcher
