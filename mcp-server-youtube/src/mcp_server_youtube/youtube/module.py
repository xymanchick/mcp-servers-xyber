import json
import logging
from functools import lru_cache
from typing import Any, Optional

# --- Third-party Imports ---
from googleapiclient.discovery import Resource, build
from googleapiclient.errors import HttpError
from mcp_server_youtube.youtube.config import (YouTubeApiError,
                                               YouTubeClientError,
                                               YouTubeConfig,
                                               YouTubeTranscriptError)
from mcp_server_youtube.utils.data_utils import DataUtils
from mcp_server_youtube.youtube.models import YouTubeVideo
from youtube_transcript_api import (
    NoTranscriptFound,
    TranscriptsDisabled,
    NoTranscriptAvailable,
    CouldNotRetrieveTranscript,
    YouTubeTranscriptApi
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
            published_after: Only include videos published after this date
            published_before: Only include videos published before this date

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

    def _get_transcript_by_id(self, video_id: str, language: str) -> str:
        """
        Fetch the transcript for a specific video ID with improved error handling.

        Args:
            video_id: The YouTube video ID to fetch transcript for.
            language: The preferred language code for the transcript.

        Returns:
            The transcript text as a string, or an error message if transcript retrieval fails.
        """
        try:
            try:
                # Get transcript list with error handling
                transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            except CouldNotRetrieveTranscript as e:
                # Handle specific transcript retrieval errors
                logger.debug(f"Could not retrieve transcript for {video_id}: {str(e).split('!')[0]}")
                return f"[Transcript unavailable: {str(e).split('!')[0]}]"
            except Exception as e:
                logger.error(f"Unexpected error listing transcripts for {video_id}: {e}", exc_info=True)
                return f"[Error listing transcripts: {str(e)}]"

            # Try to get the preferred language transcript
            try:
                transcript = transcript_list.find_transcript([language])
            except NoTranscriptFound:
                # Try automatic translation if preferred language not available
                try:
                    transcript = transcript_list.find_transcript(['en']).translate(language)
                except NoTranscriptFound:
                    # Try English transcript if translation not available
                    try:
                        transcript = transcript_list.find_transcript(['en'])
                    except NoTranscriptFound:
                        # Try any available transcript
                        try:
                            transcript = transcript_list.find_manually_created_transcript()
                        except NoTranscriptFound:
                            logger.debug(f"No transcript found for {video_id} in any language")
                            return "[No transcript available for this video]"

            # Fetch and process transcript with XML error handling
            try:
                transcript_text = " ".join([segment.text for segment in transcript.fetch()])
                if len(transcript_text) > self.max_transcript_preview:
                    return transcript_text[:self.max_transcript_preview] + "... [Preview truncated]"
                return transcript_text
            except ET.ParseError as e:
                logger.debug(f"XML parsing error for {video_id} transcript: {str(e)}")
                return f"[XML parsing error: {str(e)}]"
            except Exception as parse_error:
                logger.warning(f"Error parsing transcript for video {video_id}: {parse_error}")
                return f"[Transcript parsing error: {str(parse_error)}]"
            
        except TranscriptsDisabled:
            logger.debug(f"Transcripts disabled for video {video_id}")
            return "[Transcripts are disabled for this video]"
        except NoTranscriptAvailable:
            logger.debug(f"No transcript available for video {video_id}")
            return "[No transcript available for this video]"
        except Exception as e:
            logger.error(f"Unexpected error fetching transcript for video {video_id}: {e}", exc_info=True)
            return f"[Error fetching transcript: {str(e)}]"

    def _process_search_results(
        self,
        search_response: dict,
        language: str
    ) -> list[YouTubeVideo]:
        """
        Process the search response and fetch transcripts for each video.

        Args:
            search_response: The raw search response from YouTube Data API.
            language: The preferred language code for the transcript.

        Returns:
            A list of YouTubeVideo objects with video details and transcripts.
        """
        found_videos = []
        if "items" in search_response:
            for search_item in search_response.get("items", []):
                if self._is_valid_search_item(search_item):
                    video_id = search_item.get("id", {}).get("videoId")
                    if video_id:
                        try:
                            transcript = self._get_transcript_by_id(video_id, language)
                        except YouTubeTranscriptError as transcript_error:
                            logger.warning(f"Transcript unavailable for video {video_id}: {transcript_error}")
                            transcript = f"[Transcript unavailable: {str(transcript_error)}]"
                        except Exception as transcript_error:
                            logger.warning(f"Unexpected transcript error for video {video_id}: {transcript_error}")
                            transcript = "[Transcript unavailable: Unable to retrieve transcript]"
                        
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
            msg = f"Transcripts are disabled for video ID: {video_id}"
            logger.warning(msg)
            raise YouTubeTranscriptError(video_id=video_id, message=msg) from e

        except NoTranscriptFound as e:
            msg = (
                f"No transcript found for video ID {video_id} in language '{language}'."
            )
            logger.warning(msg)
            raise YouTubeTranscriptError(video_id=video_id, message=msg) from e

        except Exception as e:
            msg = f"Could not retrieve transcript for video ID {video_id}: {e}"
            logger.exception(msg)
            raise YouTubeTranscriptError(video_id=video_id, message=msg) from e


@lru_cache(maxsize=1)
def get_youtube_searcher() -> YouTubeSearcher:
    """Get a cached instance of YouTubeSearcher."""
    config = YouTubeConfig()
    searcher = YouTubeSearcher(config)
    return searcher