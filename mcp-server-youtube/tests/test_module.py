import json
from unittest.mock import MagicMock, Mock, patch

import pytest
from googleapiclient.errors import HttpError
from mcp_server_youtube.youtube.config import (
    YouTubeApiError,
    YouTubeClientError,
    YouTubeTranscriptError,
)
from mcp_server_youtube.youtube.models import YouTubeVideo
from mcp_server_youtube.youtube.module import YouTubeSearcher, get_youtube_searcher
from youtube_transcript_api import NoTranscriptFound, TranscriptsDisabled


class TestYouTubeSearcher:
    """Test cases for YouTubeSearcher class."""

    def test_init_success(self, mock_youtube_config):
        """Test successful YouTubeSearcher initialization."""
        with patch("mcp_server_youtube.youtube.module.build") as mock_build:
            mock_service = Mock()
            mock_build.return_value = mock_service

            searcher = YouTubeSearcher(mock_youtube_config)

            assert searcher.config == mock_youtube_config
            assert searcher.youtube_service == mock_service
            assert searcher.max_transcript_preview == 500
            mock_build.assert_called_once_with(
                "youtube", "v3", developerKey="test_api_key_123"
            )

    def test_init_failure(self, mock_youtube_config):
        """Test YouTubeSearcher initialization failure."""
        with patch("mcp_server_youtube.youtube.module.build") as mock_build:
            mock_build.side_effect = Exception("API initialization failed")

            with pytest.raises(
                YouTubeClientError,
                match="Failed to initialize YouTube Data API service",
            ):
                YouTubeSearcher(mock_youtube_config)

    def test_search_videos_success(
        self,
        mock_youtube_config,
        sample_youtube_api_response,
        sample_transcript_response,
    ):
        """Test successful video search with transcripts."""
        with (
            patch("mcp_server_youtube.youtube.module.build") as mock_build,
            patch.object(YouTubeSearcher, "_get_transcript_by_id") as mock_transcript,
        ):
            # Setup mocks
            mock_service = Mock()
            mock_build.return_value = mock_service

            # FIXED: Properly configure the mock chain
            # Mock the search().list().execute() chain to return actual dict
            mock_service.search().list().execute.return_value = (
                sample_youtube_api_response
            )

            mock_transcript.return_value = "Test transcript content"

            searcher = YouTubeSearcher(mock_youtube_config)
            results = searcher.search_videos("test query", max_results=2, language="en")

            # Assertions
            assert len(results) == 2
            assert all(isinstance(video, YouTubeVideo) for video in results)
            assert results[0].video_id == "test_video_id_1"
            assert results[0].title == "Test Video 1"
            assert results[0].transcript == "Test transcript content"
            assert results[1].video_id == "test_video_id_2"

            # Verify API calls
            mock_service.search().list.assert_called_once_with(
                q="test query", part="id,snippet", maxResults=2, type="video"
            )
            assert mock_transcript.call_count == 2

    def test_search_videos_no_results(self, mock_youtube_config):
        """Test video search with no results."""
        with patch("mcp_server_youtube.youtube.module.build") as mock_build:
            mock_service = Mock()
            mock_build.return_value = mock_service

            # FIXED: Return actual dict instead of Mock
            mock_service.search().list().execute.return_value = {"items": []}

            searcher = YouTubeSearcher(mock_youtube_config)
            results = searcher.search_videos("nonexistent query")

            assert results == []

    def test_search_videos_missing_video_id(self, mock_youtube_config):
        """Test handling of search results without video IDs."""
        with patch("mcp_server_youtube.youtube.module.build") as mock_build:
            mock_service = Mock()
            mock_build.return_value = mock_service

            # Mock response with missing videoId
            api_response = {
                "items": [
                    {
                        "kind": "youtube#searchResult",
                        "id": {
                            "kind": "youtube#video"
                            # Missing videoId
                        },
                        "snippet": {"title": "Test Video"},
                    }
                ]
            }

            # FIXED: Return actual dict
            mock_service.search().list().execute.return_value = api_response

            searcher = YouTubeSearcher(mock_youtube_config)
            results = searcher.search_videos("test query")

            assert results == []

    def test_search_videos_http_error(self, mock_youtube_config):
        """Test handling of YouTube API HTTP errors."""
        with patch("mcp_server_youtube.youtube.module.build") as mock_build:
            mock_service = Mock()
            mock_build.return_value = mock_service

            # Create mock HTTP error
            error_content = json.dumps(
                {"error": {"message": "API key invalid"}}
            ).encode("utf-8")

            mock_resp = Mock()
            mock_resp.status = 403
            http_error = HttpError(mock_resp, error_content)

            # FIXED: Configure the mock to raise the error
            mock_service.search().list().execute.side_effect = http_error

            searcher = YouTubeSearcher(mock_youtube_config)

            with pytest.raises(
                YouTubeApiError, match="YouTube API search failed: API key invalid"
            ):
                searcher.search_videos("test query")

    def test_search_videos_unexpected_error(self, mock_youtube_config):
        """Test handling of unexpected errors during search."""
        with patch("mcp_server_youtube.youtube.module.build") as mock_build:
            mock_service = Mock()
            mock_build.return_value = mock_service

            # FIXED: Configure the mock to raise the error
            mock_service.search().list().execute.side_effect = Exception(
                "Unexpected error"
            )

            searcher = YouTubeSearcher(mock_youtube_config)

            with pytest.raises(
                YouTubeClientError,
                match="An unexpected error occurred during YouTube search",
            ):
                searcher.search_videos("test query")

    def test_search_videos_transcript_error_handling(
        self, mock_youtube_config, sample_youtube_api_response
    ):
        """Test handling of transcript errors during search."""
        with (
            patch("mcp_server_youtube.youtube.module.build") as mock_build,
            patch.object(YouTubeSearcher, "_get_transcript_by_id") as mock_transcript,
        ):
            mock_service = Mock()
            mock_build.return_value = mock_service

            # FIXED: Return actual dict
            mock_service.search().list().execute.return_value = (
                sample_youtube_api_response
            )

            # First video succeeds, second fails
            mock_transcript.side_effect = [
                "Success transcript",
                YouTubeTranscriptError("test_video_id_2", "Transcript disabled"),
            ]

            searcher = YouTubeSearcher(mock_youtube_config)
            results = searcher.search_videos("test query")

            assert len(results) == 2
            assert results[0].transcript == "Success transcript"
            assert (
                "[Transcript unavailable: Transcript disabled]" in results[1].transcript
            )

    def test_get_transcript_by_id_success(
        self, mock_youtube_config, sample_transcript_response
    ):
        """Test successful transcript retrieval."""
        with (
            patch("mcp_server_youtube.youtube.module.build") as mock_build,
            patch("mcp_server_youtube.youtube.module.YouTubeTranscriptApi") as mock_api,
        ):
            mock_service = Mock()
            mock_build.return_value = mock_service

            # Mock transcript API
            mock_transcript_list = Mock()
            mock_transcript = Mock()
            mock_transcript.fetch.return_value = sample_transcript_response
            mock_transcript_list.find_transcript.return_value = mock_transcript
            mock_api.list_transcripts.return_value = mock_transcript_list

            searcher = YouTubeSearcher(mock_youtube_config)
            result = searcher._get_transcript_by_id("test_video_id", "en")

            expected_transcript = "Hello everyone, welcome to this video.\nToday we'll be discussing testing.\nLet's get started with the basics."
            assert result == expected_transcript
            mock_api.list_transcripts.assert_called_once_with("test_video_id")
            mock_transcript_list.find_transcript.assert_called_once_with(["en"])

    def test_get_transcript_by_id_no_transcript_found(self, mock_youtube_config):
        """Test handling when no transcript is found."""
        with (
            patch("mcp_server_youtube.youtube.module.build") as mock_build,
            patch("mcp_server_youtube.youtube.module.YouTubeTranscriptApi") as mock_api,
        ):
            mock_service = Mock()
            mock_build.return_value = mock_service

            mock_api.list_transcripts.side_effect = NoTranscriptFound(
                "test_video_id", [], None
            )

            searcher = YouTubeSearcher(mock_youtube_config)

            with pytest.raises(
                YouTubeTranscriptError,
                match="No transcript found for video ID test_video_id",
            ):
                searcher._get_transcript_by_id("test_video_id", "en")

    def test_get_transcript_by_id_transcripts_disabled(self, mock_youtube_config):
        """Test handling when transcripts are disabled."""
        with (
            patch("mcp_server_youtube.youtube.module.build") as mock_build,
            patch("mcp_server_youtube.youtube.module.YouTubeTranscriptApi") as mock_api,
        ):
            mock_service = Mock()
            mock_build.return_value = mock_service

            mock_api.list_transcripts.side_effect = TranscriptsDisabled("test_video_id")

            searcher = YouTubeSearcher(mock_youtube_config)

            with pytest.raises(
                YouTubeTranscriptError,
                match="Transcripts are disabled for video ID: test_video_id",
            ):
                searcher._get_transcript_by_id("test_video_id", "en")

    def test_get_transcript_by_id_unexpected_error(self, mock_youtube_config):
        """Test handling of unexpected errors during transcript retrieval."""
        with (
            patch("mcp_server_youtube.youtube.module.build") as mock_build,
            patch("mcp_server_youtube.youtube.module.YouTubeTranscriptApi") as mock_api,
        ):
            mock_service = Mock()
            mock_build.return_value = mock_service

            mock_api.list_transcripts.side_effect = Exception(
                "Unexpected transcript error"
            )

            searcher = YouTubeSearcher(mock_youtube_config)

            with pytest.raises(
                YouTubeTranscriptError,
                match="Could not retrieve transcript for video ID test_video_id",
            ):
                searcher._get_transcript_by_id("test_video_id", "en")


class TestGetYouTubeSearcher:
    """Test cases for get_youtube_searcher function."""

    @patch("mcp_server_youtube.youtube.module.YouTubeConfig")
    @patch("mcp_server_youtube.youtube.module.YouTubeSearcher")
    def test_get_youtube_searcher_caching(self, mock_searcher_class, mock_config_class):
        """Test that get_youtube_searcher properly caches instances."""
        mock_config = Mock()
        mock_searcher = Mock()
        mock_config_class.return_value = mock_config
        mock_searcher_class.return_value = mock_searcher

        # Clear any existing cache
        get_youtube_searcher.cache_clear()

        # First call
        result1 = get_youtube_searcher()

        # Second call
        result2 = get_youtube_searcher()

        # Should return the same instance (cached)
        assert result1 is result2

        # Constructor should only be called once due to caching
        mock_config_class.assert_called_once()
        mock_searcher_class.assert_called_once_with(mock_config)
