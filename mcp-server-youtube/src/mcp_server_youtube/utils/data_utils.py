from __future__ import annotations

from datetime import datetime
from datetime import timezone

from pydantic import BaseModel


class DataUtils:
    """
    Utility class for data comparison, conversion, and formatting operations.
    """

    @staticmethod
    def format_iso_datetime(dt_str: str, for_youtube_api: bool = False) -> str:
        """
        Convert a datetime string to ISO format with timezone.

        Args:
            dt_str: Input datetime string
            for_youtube_api: If True, formats datetime for YouTube API

        Returns:
            Formatted datetime string
        """
        try:
            # Normalize to include timezone
            if dt_str.endswith('Z'):
                dt_str = dt_str[:-1] + '+00:00'
            elif '+' not in dt_str and '-' not in dt_str[10:]:
                dt_str += '+00:00'

            dt = datetime.fromisoformat(dt_str)
            dt = dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

            return dt.strftime('%Y-%m-%dT%H:%M:%S.%fZ') if for_youtube_api else dt.isoformat()

        except ValueError as e:
            raise ValueError(f'Invalid datetime format: {e}') from e

    @staticmethod
    def compare_datetimes(dt1: str, dt2: str) -> int:
        """
        Compare two datetime strings.

        Args:
            dt1: First datetime
            dt2: Second datetime

        Returns:
            -1 if dt1 < dt2, 0 if equal, 1 if dt1 > dt2
        """
        try:
            dt1_parsed = datetime.fromisoformat(DataUtils.format_iso_datetime(dt1))
            dt2_parsed = datetime.fromisoformat(DataUtils.format_iso_datetime(dt2))

            return (dt1_parsed > dt2_parsed) - (dt1_parsed < dt2_parsed)

        except ValueError as e:
            raise ValueError(f'Invalid datetime comparison: {e}') from e

    @staticmethod
    def validate_date_range(start_date: str | None, end_date: str | None) -> None:
        """
        Ensure start_date is not after end_date.

        Args:
            start_date: Start date string
            end_date: End date string

        Raises:
            ValueError: If start_date > end_date
        """
        if start_date and end_date:
            if DataUtils.compare_datetimes(start_date, end_date) > 0:
                raise ValueError('Start date cannot be after end date')

    @staticmethod
    def format_video_data(video_data: dict | None) -> dict | None:
        """
        Extract and format video data from raw YouTube API response.

        Args:
            video_data: Raw video metadata dictionary

        Returns:
            Cleaned and formatted video data dictionary
        """
        if not video_data:
            return None

        snippet = video_data.get('snippet', {})
        return {
            'video_id': video_data.get('id', {}).get('videoId', 'N/A'),
            'title': snippet.get('title', 'N/A'),
            'description': snippet.get('description', ''),
            'channel': snippet.get('channelTitle', 'N/A'),
            'published_at': DataUtils.format_iso_datetime(snippet.get('publishedAt', 'N/A')),
            'thumbnail': snippet.get('thumbnails', {}).get('default', {}).get('url', 'N/A'),
        }

    @staticmethod
    def format_response_data(videos: list[BaseModel]) -> dict:
        """
        Format a list of video models for API output.

        Args:
            videos: List of Pydantic video model instances

        Returns:
            Dictionary suitable for JSON API response
        """
        return {
            'results': [
                {
                    'video_id': v.video_id,
                    'title': v.title,
                    'channel': v.channel,
                    'published_at': v.published_at,
                    'thumbnail': v.thumbnail,
                    'description': v.description,
                    'transcript': v.transcript,
                }
                for v in videos
            ],
            'total_results': len(videos),
        }
