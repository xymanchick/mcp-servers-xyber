from datetime import datetime, timezone
from typing import Optional, Dict, Any
import re
from pydantic import BaseModel

class DataUtils:
    """
    Utility class for data comparison, conversion, and formatting operations.
    """

    @staticmethod
    def format_iso_datetime(dt_str: str, for_youtube_api: bool = False) -> str:
        """
        Format a datetime string to ISO format with timezone.

        Args:
            dt_str: Input datetime string in ISO format
            for_youtube_api: If True, formats the datetime for YouTube API

        Returns:
            Formatted datetime string with timezone
        """
        try:
            # Handle both Z and ±HH:MM timezone formats
            if dt_str.endswith('Z'):
                dt_str = dt_str[:-1] + '+00:00'
            elif '+' not in dt_str and '-' not in dt_str:
                dt_str = dt_str + '+00:00'
            
            dt = datetime.fromisoformat(dt_str)
            if not dt.tzinfo:
                dt = dt.replace(tzinfo=timezone.utc)
            
            # Format for YouTube API if requested
            if for_youtube_api:
                return dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            
            return dt.isoformat()
        except ValueError as e:
            raise ValueError(f"Invalid datetime format: {str(e)}") from e

    @staticmethod
    def compare_datetimes(dt1: str, dt2: str) -> int:
        """
        Compare two datetime strings.

        Args:
            dt1: First datetime string
            dt2: Second datetime string

        Returns:
            -1 if dt1 < dt2
            0 if dt1 == dt2
            1 if dt1 > dt2
        """
        try:
            dt1 = datetime.fromisoformat(DataUtils.format_iso_datetime(dt1))
            dt2 = datetime.fromisoformat(DataUtils.format_iso_datetime(dt2))
            
            if dt1 < dt2:
                return -1
            elif dt1 > dt2:
                return 1
            return 0
        except ValueError as e:
            raise ValueError(f"Invalid datetime comparison: {str(e)}") from e

    @staticmethod
    def validate_date_range(start_date: Optional[str], end_date: Optional[str]) -> None:
        """
        Validate that a date range is valid (start_date <= end_date).

        Args:
            start_date: Start date string
            end_date: End date string

        Raises:
            ValueError: If the date range is invalid
        """
        if not start_date or not end_date:
            return
            
        if DataUtils.compare_datetimes(start_date, end_date) > 0:
            raise ValueError("Start date cannot be after end date")

    @staticmethod
    def format_video_data(video_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format video data from YouTube API response.

        Args:
            video_data: Raw video data dictionary

        Returns:
            Formatted video data dictionary
        """
        formatted = {
            'video_id': video_data.get('id', {}).get('videoId', 'N/A'),
            'title': video_data.get('snippet', {}).get('title', 'N/A'),
            'description': video_data.get('snippet', {}).get('description', ''),
            'channel': video_data.get('snippet', {}).get('channelTitle', 'N/A'),
            'published_at': DataUtils.format_iso_datetime(
                video_data.get('snippet', {}).get('publishedAt', 'N/A')
            ),
            'thumbnail': video_data.get('snippet', {}).get('thumbnails', {})
                .get('default', {}).get('url', 'N/A')
        }
        return formatted

    @staticmethod
    def format_response_data(videos: list[BaseModel]) -> Dict[str, Any]:
        """
        Format response data for API output.

        Args:
            videos: List of video models

        Returns:
            Formatted response dictionary
        """
        return {
            'results': [
                {
                    'video_id': video.video_id,
                    'title': video.title,
                    'channel': video.channel,
                    'published_at': video.published_at,
                    'thumbnail': video.thumbnail,
                    'description': video.description,
                    'transcript': video.transcript
                }
                for video in videos
            ],
            'total_results': len(videos)
        }
