import json
import logging
import xml
from datetime import datetime
from functools import lru_cache
from typing import Any, Optional, Dict, List
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
    FetchedTranscriptSnippet
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

    def _create_video_from_search_item(self, search_item: dict, transcript: str) -> YouTubeVideo:
        """
        Create a YouTubeVideo object from a search item and transcript.

        Args:
            search_item: A search result item from YouTube Data API.
            transcript: The video's transcript text.

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
            transcript=transcript
        )

    def _get_friendly_transcript_message(self, video_id: str, error: Exception) -> str:
        """
        Convert technical transcript errors into user-friendly messages.
        
        Args:
            video_id: The video ID that failed
            error: The exception that occurred
            
        Returns:
            A user-friendly message explaining why the transcript isn't available
        """
        error_str = str(error).lower()
        
        # Map technical errors to friendly messages
        if "transcripts are disabled" in error_str:
            return "[Transcripts disabled by creator]"
        elif "no transcript found" in error_str:
            return "[No transcript available in requested language]"
        elif "no element found" in error_str or "xml" in error_str or "parse" in error_str:
            return "[Transcript data corrupted or unavailable]"
        elif "could not retrieve" in error_str:
            return "[Transcript temporarily unavailable]"
        elif "forbidden" in error_str or "403" in error_str:
            return "[Transcript access restricted]"
        elif "not found" in error_str or "404" in error_str:
            return "[Video or transcript not found]"
        else:
            return "[Transcript unavailable]"

    def _get_transcript_by_id(self, video_id: str, language: str) -> str:
        """
        Fetches the transcript for a given YouTube video ID with improved error handling.
        
        Args:
            video_id: The unique ID of the YouTube video.
            language: The preferred language code for the transcript.
            
        Returns:
            A string containing the transcript data or a friendly error message.
        """
        try:
            # Get transcript list first to check availability
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        except TranscriptsDisabled as e:
            # Transcripts are disabled by creator
            logger.warning(f"Transcripts disabled for video ID {video_id}")
            return "[Transcripts disabled by creator]"
        except NoTranscriptFound as e:
            # Transcript not found in requested language
            logger.warning(f"No transcript found for video ID {video_id} in language '{language}'")
            return "[No transcript available in requested language]"
        except (xml.etree.ElementTree.ParseError, xml.parsers.expat.ExpatError) as e:
            # XML parsing error - usually indicates corrupted data
            logger.warning(f"XML parsing error for video {video_id}: {e}")
            return "[Transcript data corrupted or unavailable]"
        except CouldNotRetrieveTranscript as e:
            # Network/API error - temporary issue
            logger.warning(f"Could not retrieve transcript for video {video_id}: {e}")
            return "[Transcript temporarily unavailable]"
        except requests.exceptions.ConnectionError as e:
            # Connection error (DNS, timeout, etc.)
            logger.error(f"Connection error while fetching transcript for video {video_id}: {e}")
            return "[Connection error: Unable to reach YouTube]"
        except requests.exceptions.Timeout as e:
            # Request timeout
            logger.warning(f"Timeout while fetching transcript for video {video_id}: {e}")
            return "[Request timed out: Please try again later]"
        except requests.exceptions.RequestException as e:
            # Other HTTP request errors
            logger.error(f"HTTP error while fetching transcript for video {video_id}: {e}")
            return "[HTTP error: Unable to fetch transcript]"
        except Exception as e:
            # Catch any other unexpected errors
            logger.exception(f"Unexpected error while fetching transcript for video {video_id}: {e}")
            return "[Transcript unavailable due to unexpected error]"

        # Try to get transcript with fallback logic
        try:
            # 1. Try preferred language
            transcript = transcript_list.find_transcript([language])
        except NoTranscriptFound:
            try:
                # 2. Try English
                transcript = transcript_list.find_transcript(['en'])
            except NoTranscriptFound:
                try:
                    # 3. Try any manually created transcript
                    transcript = transcript_list.find_manually_created_transcript()
                except NoTranscriptFound:
                    logger.debug(f"No manual transcripts available for video {video_id}")
                    return "[No transcript available in any language]"

        # Fetch transcript with comprehensive error handling
        try:
            transcript_entries = transcript.fetch()
            
            # Handle both dictionary format and FetchedTranscriptSnippet objects
            transcript_text_parts = []
            for entry in transcript_entries:
                if hasattr(entry, 'text'):
                    # New format: FetchedTranscriptSnippet object
                    transcript_text_parts.append(entry.text)
                elif isinstance(entry, dict) and 'text' in entry:
                    # Old format: dictionary
                    transcript_text_parts.append(entry['text'])
                else:
                    # Fallback: convert to string
                    transcript_text_parts.append(str(entry))

            if not transcript_text_parts:
                return "[Transcript appears to be empty]"
                
            transcript_text = " ".join(transcript_text_parts)
            
            # Truncate if too long
            if len(transcript_text) > self.max_transcript_preview:
                transcript_text = transcript_text[:self.max_transcript_preview] + "..."
                
            return transcript_text

        except ET.ParseError as e:
            logger.debug(f"XML parsing error for video {video_id}: {e}")
            return "[Transcript data corrupted]"
        except Exception as e:
            logger.debug(f"Error fetching transcript for video {video_id}: {e}")
            return self._get_friendly_transcript_message(video_id, e)

    def _process_search_results(
        self,
        search_response: dict,
        language: str
    ) -> List[YouTubeVideo]:
        """Process the search response and fetch transcripts for each video."""
        found_videos = []
        transcript_stats = {'success': 0, 'failed': 0, 'disabled': 0}
        
        if "items" in search_response:
            for search_item in search_response.get("items", []):
                if self._is_valid_search_item(search_item):
                    video_id = search_item.get("id", {}).get("videoId")
                    if video_id:
                        # Get transcript with improved error handling
                        transcript = self._get_transcript_by_id(video_id, language)
                        
                        # Update statistics
                        if transcript.startswith('['):
                            if 'disabled' in transcript.lower():
                                transcript_stats['disabled'] += 1
                            else:
                                transcript_stats['failed'] += 1
                        else:
                            transcript_stats['success'] += 1
                        
                        video = self._create_video_from_search_item(search_item, transcript)
                        found_videos.append(video)
                    else:
                        logger.warning(f"Search item found without a videoId: {search_item}")
        return found_videos

    def search_videos(
        self, 
        query: str, 
        max_results: int = 15, 
        language: str = "en",
        published_after: Optional[str] = None,
        published_before: Optional[str] = None,
        order_by: Optional[str] = None
    ) -> list[YouTubeVideo]:
        """
        Performs the video search using the YouTube Data API and fetches transcripts.

        Args:
            query: The search term for YouTube videos.
            max_results: Maximum number of results to return.
            language: The preferred language code for the transcript.
            published_after: Only include videos published after this date (ISO format)
            published_before: Only include videos published before this date (ISO format)
            order_by: Sort order for search results (relevance, date, viewCount, rating)

        Returns:
            A list of YouTubeVideo objects with video details and transcripts.

        Raises:
            YouTubeApiError: If a YouTube Data API error occurs.
            YouTubeTranscriptError: If a transcript retrieval error occurs.
            YouTubeClientError: For other unexpected errors during the search.
        """
        try:
            logger.info(
                f"Searching YouTube for query: '{query}' with max_results={max_results}"
            )

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

            # Process results and fetch transcripts
            found_videos = self._process_search_results(search_response, language)

            logger.info(f"Found {len(found_videos)} video(s) for query: '{query}'")
            return found_videos

        except HttpError as e:
            error_details = {}
            try:
                error_content = e.content.decode("utf-8")
                error_details = json.loads(error_content)
                error_message = error_details.get("error", {}).get(
                    "message", error_content
                )
            except (json.JSONDecodeError, UnicodeDecodeError):
                error_message = str(e)

            status_code = e.resp.status
            msg = f"YouTube API search failed: {error_message}"
            logger.error(f"{msg} (HTTP Status: {status_code})", exc_info=True)
            raise YouTubeApiError(
                msg, status_code=status_code, details=error_details
            ) from e

        except Exception as e:
            # Catch-all for other unexpected errors during search/transcript process
            msg = f"An unexpected error occurred during YouTube search or transcript retrieval: {e}"
            logger.error(msg, exc_info=True)
            raise YouTubeClientError(msg) from e

    def _get_transcript_by_id(self, video_id: str, language: str) -> str:
        """
        Fetches the transcript for a given YouTube video ID.

        Args:
            video_id: The unique ID of the YouTube video.
            language: The preferred language code for the transcript.

        Returns:
            A string containing the transcript data.

        Raises:
            YouTubeTranscriptError: If the transcript cannot be fetched.
        """
        logger.debug(
            f"Attempting to fetch transcript for video ID: {video_id} in language: {language}"
        )
        try:
            # Fetch the transcript list and try the specified language
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            transcript = transcript_list.find_transcript([language])

            # Fetch the actual transcript data
            transcript_entries = transcript.fetch()

            # Handle both dictionary format and FetchedTranscriptSnippet objects
            transcript_text_parts = []
            for entry in transcript_entries:
                if hasattr(entry, 'text'):
                    # New format: FetchedTranscriptSnippet object
                    transcript_text_parts.append(entry.text)
                elif isinstance(entry, dict) and 'text' in entry:
                    # Old format: dictionary
                    transcript_text_parts.append(entry['text'])
                else:
                    # Fallback: convert to string
                    transcript_text_parts.append(str(entry))

            transcript_text = "\n".join(transcript_text_parts)
            logger.info(f"Successfully fetched transcript for video ID: {video_id}")
            return transcript_text
        except TranscriptsDisabled as e:
            # Transcripts are disabled by creator
            logger.warning(f"Transcripts disabled for video ID {video_id}")
            return "[Transcripts disabled by creator]"
        except requests.exceptions.RequestException as e:
            # Handle other HTTP request errors
            logger.error(f"HTTP error while fetching transcript for video {video_id}: {e}")
            return "[HTTP error: Unable to fetch transcript]"
        except Exception as e:
            # Catch any other unexpected errors
            logger.exception(f"Unexpected error while fetching transcript for video {video_id}: {e}")
            return "[Transcript unavailable due to unexpected error]"

@lru_cache(maxsize=1)
def get_youtube_searcher() -> YouTubeSearcher:
    """Get a cached instance of YouTubeSearcher."""
    config = YouTubeConfig()
    searcher = YouTubeSearcher(config)
    return searcher