import os
import logging
import xml.etree.ElementTree as ET
from typing import List, Optional, Dict, Any
from datetime import datetime
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    NoTranscriptFound,
    TranscriptsDisabled,
    NoTranscriptAvailable,
    CouldNotRetrieveTranscript
)

logger = logging.getLogger(__name__)


class YouTubeClientError(Exception):
    """Base exception for YouTube client errors."""
    pass


class YouTubeApiError(YouTubeClientError):
    """Exception for YouTube API errors."""
    pass


class YouTubeTranscriptError(YouTubeClientError):
    """Exception for transcript retrieval errors."""
    pass


class YouTubeVideo:
    """Wrapper class for YouTube video data."""

    def __init__(self, video_data: Dict[str, Any]):
        self.video_id = video_data['video_id']
        self.title = video_data['title']
        self.channel = video_data['channel']
        self.published_at = video_data['published_at']
        self.thumbnail = video_data['thumbnail']
        self.description = video_data['description']
        self.transcript = video_data['transcript']

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            'video_id': self.video_id,
            'title': self.title,
            'channel': self.channel,
            'published_at': self.published_at,
            'thumbnail': self.thumbnail,
            'description': self.description,
            'transcript': self.transcript
        }


class YouTubeSearcher:
    """Class for searching YouTube videos and retrieving transcripts."""

    def __init__(self, api_key: str):
        """Initialize YouTube client."""
        self.api_key = api_key
        self.youtube = build('youtube', 'v3', developerKey=api_key)

    def search_videos(
            self,
            query: str,
            max_results: int = 10,
            language: str = "en",
            published_after: Optional[datetime] = None,
            published_before: Optional[datetime] = None,
            return_objects: bool = False
    ) -> List[Any]:
        """
        Search YouTube videos and retrieve transcripts.

        Args:
            query: Search query string
            max_results: Maximum number of results to return
            language: Language code for transcript (e.g., 'en', 'es')
            published_after: Only include videos published after this date
            published_before: Only include videos published before this date
            return_objects: If True, returns YouTubeVideo objects instead of dicts

        Returns:
            List of video results (either dicts or YouTubeVideo objects)

        Raises:
            YouTubeApiError: If there's an error with the YouTube API
            YouTubeTranscriptError: If there's an error with transcript retrieval
        """
        try:
            # Convert datetimes to RFC 3339 format
            published_after_str = published_after.isoformat() if published_after else None
            published_before_str = published_before.isoformat() if published_before else None

            # Search videos
            request = self.youtube.search().list(
                part="id,snippet",
                q=query,
                type="video",
                maxResults=max_results,
                publishedAfter=published_after_str,
                publishedBefore=published_before_str,
                order="relevance"
            )

            response = request.execute()
            items = response.get('items', [])

            results = []
            for item in items:
                video_id = item['id']['videoId']
                video_data = {
                    'video_id': video_id,
                    'title': item['snippet']['title'],
                    'channel': item['snippet']['channelTitle'],
                    'published_at': item['snippet']['publishedAt'],
                    'thumbnail': item['snippet']['thumbnails']['high']['url'],
                    'description': item['snippet']['description'],
                    'transcript': None
                }

                try:
                    # Try to get transcript with improved error handling
                    transcript = YouTubeTranscriptApi.get_transcript(
                        video_id,
                        languages=[language, 'en']
                    )
                    video_data['transcript'] = " ".join([t['text'] for t in transcript])
                except (NoTranscriptFound, TranscriptsDisabled, NoTranscriptAvailable):
                    logger.warning(f"No transcript found for video {video_id}")
                except CouldNotRetrieveTranscript as e:
                    logger.error(f"Could not retrieve transcript for video {video_id}: {str(e)}")
                except ET.ParseError as e:
                    logger.error(f"XML parsing error for video {video_id}: {str(e)}")
                    video_data['transcript'] = None
                except Exception as e:
                    logger.error(f"Unexpected transcript error for video {video_id}: {str(e)}", exc_info=True)
                    raise YouTubeTranscriptError(f"Transcript error for video {video_id}") from e

                if return_objects:
                    results.append(YouTubeVideo(video_data))
                else:
                    results.append(video_data)

            return results

        except HttpError as e:
            logger.error(f"YouTube API error: {str(e)}", exc_info=True)
            raise YouTubeApiError(f"YouTube API error: {str(e)}") from e
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            raise YouTubeClientError(f"Unexpected error: {str(e)}") from e


def get_youtube_searcher() -> YouTubeSearcher:
    """Get YouTubeSearcher instance with API key from environment."""
    api_key = os.getenv('YOUTUBE_API_KEY')
    if not api_key:
        raise YouTubeClientError("YOUTUBE_API_KEY environment variable not set")
    return YouTubeSearcher(api_key)