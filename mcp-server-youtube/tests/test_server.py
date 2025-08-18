import pytest
from unittest.mock import Mock, patch, AsyncMock
from contextlib import asynccontextmanager

from fastapi.testclient import TestClient
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from mcp_server_youtube.server import app_lifespan, youtube_search_and_transcript, app
from mcp_server_youtube.youtube import YouTubeClientError
from mcp_server_youtube.youtube.youtube_errors import (
    YouTubeApiError,
    ServiceUnavailableError,
    InvalidResponseError,
    QuotaExceededError,
    ValidationError,
    VideoNotFoundError,
    TranscriptNotAvailableError,
)
from mcp_server_youtube.youtube.models import YouTubeVideo


class TestAppLifespan:
    """Test cases for app_lifespan context manager."""

    @pytest.mark.asyncio
    async def test_app_lifespan_success(self):
        """Test successful app lifespan initialization."""
        mock_server = Mock(spec=FastMCP)
        mock_searcher = Mock()
        
        with patch('mcp_server_youtube.server.get_youtube_searcher') as mock_get_searcher:
            mock_get_searcher.return_value = mock_searcher
            
            async with app_lifespan(mock_server) as context:
                assert "youtube_searcher" in context
                assert context["youtube_searcher"] is mock_searcher
            
            mock_get_searcher.assert_called_once()

    @pytest.mark.asyncio
    async def test_app_lifespan_youtube_client_error(self):
        """Test app lifespan with YouTubeClientError during initialization."""
        mock_server = Mock(spec=FastMCP)
        
        with patch('mcp_server_youtube.server.get_youtube_searcher') as mock_get_searcher:
            mock_get_searcher.side_effect = YouTubeClientError("API key invalid")
            
            with pytest.raises(YouTubeClientError, match="API key invalid"):
                async with app_lifespan(mock_server):
                    pass

    @pytest.mark.asyncio
    async def test_app_lifespan_unexpected_error(self):
        """Test app lifespan with unexpected error during initialization."""
        mock_server = Mock(spec=FastMCP)
        
        with patch('mcp_server_youtube.server.get_youtube_searcher') as mock_get_searcher:
            mock_get_searcher.side_effect = Exception("Unexpected initialization error")
            
            with pytest.raises(Exception, match="Unexpected initialization error"):
                async with app_lifespan(mock_server):
                    pass


class TestYouTubeSearchAndTranscript:
    """Test cases for youtube_search_and_transcript tool."""

    def create_mock_context(self, youtube_searcher):
        """Helper to create mock context with youtube_searcher."""
        context = Mock()
        context.request_context = Mock()
        context.request_context.lifespan_context = {"youtube_searcher": youtube_searcher}
        return context

    @pytest.mark.asyncio
    async def test_youtube_search_and_transcript_success(self, sample_youtube_video):
        """Test successful YouTube search and transcript retrieval."""
        mock_searcher = Mock()
        mock_searcher.search_videos.return_value = [sample_youtube_video]
        
        context = self.create_mock_context(mock_searcher)
        
        result = await youtube_search_and_transcript(
            ctx=context,
            query="test query",
            max_results=1,
            transcript_language="en"
        )
        
        # Verify the searcher was called correctly
        mock_searcher.search_videos.assert_called_once_with(
            query="test query",
            max_results=1,
            language="en"
        )
        
        # Verify the result format
        assert str(sample_youtube_video) in result

    @pytest.mark.asyncio
    async def test_youtube_search_and_transcript_multiple_videos(self):
        """Test YouTube search returning multiple videos."""
        video1 = YouTubeVideo(
            video_id="id1",
            title="Video 1",
            description="Desc 1",
            channel="Channel 1",
            published_at="2024-01-01",
            thumbnail="thumb1.jpg",
            transcript="Transcript 1"
        )
        video2 = YouTubeVideo(
            video_id="id2", 
            title="Video 2",
            description="Desc 2",
            channel="Channel 2",
            published_at="2024-01-02",
            thumbnail="thumb2.jpg",
            transcript="Transcript 2"
        )
        
        mock_searcher = Mock()
        mock_searcher.search_videos.return_value = [video1, video2]
        
        context = self.create_mock_context(mock_searcher)
        
        result = await youtube_search_and_transcript(
            ctx=context,
            query="test query",
            max_results=2
        )
        
        # Verify both videos are in the result, separated by commas and newlines
        assert str(video1) in result
        assert str(video2) in result
        assert ",\n\n" in result

    @pytest.mark.asyncio
    async def test_youtube_search_and_transcript_default_params(self):
        """Test YouTube search with default parameters."""
        mock_searcher = Mock()
        mock_searcher.search_videos.return_value = []
        
        context = self.create_mock_context(mock_searcher)
        
        await youtube_search_and_transcript(ctx=context, query="test query")
        
        # Verify default parameters are used
        mock_searcher.search_videos.assert_called_once_with(
            query="test query",
            max_results=3,  # Default value
            language="en"   # Default value
        )

    @pytest.mark.asyncio
    async def test_youtube_search_and_transcript_custom_params(self):
        """Test YouTube search with custom parameters."""
        mock_searcher = Mock()
        mock_searcher.search_videos.return_value = []
        
        context = self.create_mock_context(mock_searcher)
        
        await youtube_search_and_transcript(
            ctx=context,
            query="custom query",
            max_results=5,
            transcript_language="es"
        )
        
        mock_searcher.search_videos.assert_called_once_with(
            query="custom query",
            max_results=5,
            language="es"
        )

    @pytest.mark.asyncio
    async def test_youtube_search_and_transcript_empty_results(self):
        """Test YouTube search returning no results."""
        mock_searcher = Mock()
        mock_searcher.search_videos.return_value = []
        
        context = self.create_mock_context(mock_searcher)
        
        result = await youtube_search_and_transcript(ctx=context, query="nonexistent")
        
        assert result == ""  # Empty join result

    @pytest.mark.asyncio
    async def test_youtube_search_and_transcript_youtube_client_error(self):
        """Test handling of YouTubeClientError."""
        mock_searcher = Mock()
        mock_searcher.search_videos.side_effect = YouTubeClientError("API quota exceeded")
        
        context = self.create_mock_context(mock_searcher)
        
        with pytest.raises(ToolError, match="YouTube client error: API quota exceeded"):
            await youtube_search_and_transcript(ctx=context, query="test query")

    @pytest.mark.asyncio
    async def test_youtube_search_and_transcript_unexpected_error(self):
        """Test handling of unexpected errors."""
        mock_searcher = Mock()
        mock_searcher.search_videos.side_effect = Exception("Unexpected error")
        
        context = self.create_mock_context(mock_searcher)
        
        with pytest.raises(ToolError, match="An unexpected error occurred during search"):
            await youtube_search_and_transcript(ctx=context, query="test query")

    @pytest.mark.asyncio
    async def test_youtube_search_and_transcript_parameter_validation(self):
        """Test parameter validation and edge cases."""
        mock_searcher = Mock()
        mock_searcher.search_videos.return_value = []
        
        context = self.create_mock_context(mock_searcher)
        
        # Test with minimal parameters
        await youtube_search_and_transcript(ctx=context, query="")
        mock_searcher.search_videos.assert_called_with(
            query="",
            max_results=3,
            language="en"
        )
        
        # Test with boundary values
        await youtube_search_and_transcript(
            ctx=context,
            query="test",
            max_results=1,
            transcript_language=""
        )
        mock_searcher.search_videos.assert_called_with(
            query="test",
            max_results=1,
            language=""
        )

    @pytest.mark.asyncio
    async def test_youtube_search_and_transcript_context_access(self):
        """Test proper context access and lifespan context retrieval."""
        mock_searcher = Mock()
        mock_searcher.search_videos.return_value = []
        
        # Test with missing lifespan context
        context = Mock()
        context.request_context = Mock()
        context.request_context.lifespan_context = {}
        
        with pytest.raises(KeyError):
            await youtube_search_and_transcript(ctx=context, query="test")
        
        # Test with valid context
        context.request_context.lifespan_context = {"youtube_searcher": mock_searcher}
        await youtube_search_and_transcript(ctx=context, query="test")
        mock_searcher.search_videos.assert_called_once()

    @pytest.mark.asyncio
    async def test_youtube_search_and_transcript_service_unavailable_error(self):
        """Test handling of ServiceUnavailableError."""
        mock_searcher = Mock()
        mock_searcher.search_videos.side_effect = ServiceUnavailableError("Service is unavailable")
        
        context = self.create_mock_context(mock_searcher)
        
        with pytest.raises(ToolError, match="YouTube service is unavailable"):
            await youtube_search_and_transcript(ctx=context, query="test query")

    @pytest.mark.asyncio
    async def test_youtube_search_and_transcript_invalid_response_error(self):
        """Test handling of InvalidResponseError."""
        mock_searcher = Mock()
        mock_searcher.search_videos.side_effect = InvalidResponseError("Invalid response from YouTube")
        
        context = self.create_mock_context(mock_searcher)
        
        with pytest.raises(ToolError, match="Invalid response from YouTube"):
            await youtube_search_and_transcript(ctx=context, query="test query")

    @pytest.mark.asyncio
    async def test_youtube_search_and_transcript_quota_exceeded_error(self):
        """Test handling of QuotaExceededError."""
        mock_searcher = Mock()
        mock_searcher.search_videos.side_effect = QuotaExceededError("Quota exceeded")
        
        context = self.create_mock_context(mock_searcher)
        
        with pytest.raises(ToolError, match="YouTube quota exceeded"):
            await youtube_search_and_transcript(ctx=context, query="test query")

    @pytest.mark.asyncio
    async def test_youtube_search_and_transcript_validation_error(self):
        """Test handling of ValidationError."""
        mock_searcher = Mock()
        mock_searcher.search_videos.side_effect = ValidationError("Invalid query parameters")
        
        context = self.create_mock_context(mock_searcher)
        
        with pytest.raises(ToolError, match="Invalid query parameters"):
            await youtube_search_and_transcript(ctx=context, query="test query")

    @pytest.mark.asyncio
    async def test_youtube_search_and_transcript_video_not_found_error(self):
        """Test handling of VideoNotFoundError."""
        mock_searcher = Mock()
        mock_searcher.search_videos.side_effect = VideoNotFoundError("Video not found")
        
        context = self.create_mock_context(mock_searcher)
        
        with pytest.raises(ToolError, match="Video not found"):
            await youtube_search_and_transcript(ctx=context, query="test query")

    @pytest.mark.asyncio
    async def test_youtube_search_and_transcript_transcript_not_available_error(self):
        """Test handling of TranscriptNotAvailableError."""
        mock_searcher = Mock()
        mock_searcher.search_videos.side_effect = TranscriptNotAvailableError("Transcript not available")
        
        context = self.create_mock_context(mock_searcher)
        
        with pytest.raises(ToolError, match="Transcript not available"):
            await youtube_search_and_transcript(ctx=context, query="test query")


class TestStructuredErrorHandling:
    """Test cases for structured error handling and HTTP responses."""

    def test_youtube_api_error_response(self):
        """Test that YouTubeApiError returns proper structured response."""
        client = TestClient(app)
        
        with patch('mcp_server_youtube.server.get_youtube_searcher') as mock_get_searcher:
            mock_searcher = Mock()
            mock_searcher.search_videos.side_effect = YouTubeApiError("API rate limit exceeded")
            mock_get_searcher.return_value = mock_searcher
            
            # Test a route that would trigger the exception
            response = client.get("/health")  # This should work fine
            assert response.status_code == 200
            
            # For direct exception testing, we need to test the handler
            from mcp_server_youtube.utils.exception_handler import youtube_exception_handler
            from fastapi import Request
            
            request = Mock(spec=Request)
            request.url.path = "/test"
            request.method = "GET"
            request.headers.get.return_value = "test-agent"
            
            exc = YouTubeApiError("Test API error")
            
            # Test the exception handler directly
            import asyncio
            response = asyncio.run(youtube_exception_handler(request, exc))
            
            assert response.status_code == 502
            response_data = response.body.decode()
            import json
            parsed_response = json.loads(response_data)
            
            assert parsed_response["error_type"] == "YOUTUBE_API_ERROR"
            assert parsed_response["message"] == "Test API error"
            assert parsed_response["status_code"] == 502

    def test_service_unavailable_error_response(self):
        """Test that ServiceUnavailableError returns proper structured response."""
        from mcp_server_youtube.utils.exception_handler import youtube_exception_handler
        from fastapi import Request
        
        request = Mock(spec=Request)
        request.url.path = "/test"
        request.method = "POST"
        request.headers.get.return_value = "test-agent"
        
        exc = ServiceUnavailableError("YouTube service is down")
        
        import asyncio
        response = asyncio.run(youtube_exception_handler(request, exc))
        
        assert response.status_code == 503
        response_data = response.body.decode()
        import json
        parsed_response = json.loads(response_data)
        
        assert parsed_response["error_type"] == "SERVICE_UNAVAILABLE"
        assert parsed_response["message"] == "YouTube service is down"
        assert parsed_response["status_code"] == 503

    def test_validation_error_response(self):
        """Test that ValidationError returns proper structured response."""
        from mcp_server_youtube.utils.exception_handler import youtube_exception_handler
        from fastapi import Request
        
        request = Mock(spec=Request)
        request.url.path = "/search"
        request.method = "POST"
        request.headers.get.return_value = "test-agent"
        
        exc = ValidationError("Invalid query parameter: max_results must be between 1 and 50")
        
        import asyncio
        response = asyncio.run(youtube_exception_handler(request, exc))
        
        assert response.status_code == 400
        response_data = response.body.decode()
        import json
        parsed_response = json.loads(response_data)
        
        assert parsed_response["error_type"] == "VALIDATION_ERROR"
        assert "Invalid query parameter" in parsed_response["message"]
        assert parsed_response["status_code"] == 400

    def test_quota_exceeded_error_response(self):
        """Test that QuotaExceededError returns proper structured response."""
        from mcp_server_youtube.utils.exception_handler import youtube_exception_handler
        from fastapi import Request
        
        request = Mock(spec=Request)
        request.url.path = "/search"
        request.method = "GET"
        request.headers.get.return_value = "test-agent"
        
        exc = QuotaExceededError("Daily quota limit exceeded")
        
        import asyncio
        response = asyncio.run(youtube_exception_handler(request, exc))
        
        assert response.status_code == 429
        response_data = response.body.decode()
        import json
        parsed_response = json.loads(response_data)
        
        assert parsed_response["error_type"] == "QUOTA_EXCEEDED"
        assert parsed_response["message"] == "Daily quota limit exceeded"
        assert parsed_response["status_code"] == 429

    def test_generic_exception_handler(self):
        """Test that generic exception handler returns proper structured response."""
        from mcp_server_youtube.utils.exception_handler import generic_exception_handler
        from fastapi import Request
        
        request = Mock(spec=Request)
        request.url.path = "/unknown"
        request.method = "GET" 
        request.headers.get.return_value = "test-agent"
        
        exc = Exception("Unexpected database connection error")
        
        import asyncio
        response = asyncio.run(generic_exception_handler(request, exc))
        
        assert response.status_code == 500
        response_data = response.body.decode()
        import json
        parsed_response = json.loads(response_data)
        
        assert parsed_response["error_type"] == "INTERNAL_SERVER_ERROR"
        assert parsed_response["message"] == "An unexpected error occurred. Please try again later."
        assert parsed_response["status_code"] == 500

    def test_video_not_found_error_response(self):
        """Test that VideoNotFoundError returns proper structured response."""
        from mcp_server_youtube.utils.exception_handler import youtube_exception_handler
        from fastapi import Request
        
        request = Mock(spec=Request)
        request.url.path = "/video/abc123"
        request.method = "GET"
        request.headers.get.return_value = "test-agent"
        
        exc = VideoNotFoundError("Video with ID 'abc123' not found")
        
        import asyncio
        response = asyncio.run(youtube_exception_handler(request, exc))
        
        assert response.status_code == 404
        response_data = response.body.decode()
        import json
        parsed_response = json.loads(response_data)
        
        assert parsed_response["error_type"] == "VIDEO_NOT_FOUND"
        assert "abc123" in parsed_response["message"]
        assert parsed_response["status_code"] == 404

    def test_transcript_not_available_error_response(self):
        """Test that TranscriptNotAvailableError returns proper structured response."""
        from mcp_server_youtube.utils.exception_handler import youtube_exception_handler
        from fastapi import Request
        
        request = Mock(spec=Request)
        request.url.path = "/transcript/xyz789"
        request.method = "GET"
        request.headers.get.return_value = "test-agent"
        
        exc = TranscriptNotAvailableError("Transcript disabled by video creator")
        
        import asyncio
        response = asyncio.run(youtube_exception_handler(request, exc))
        
        assert response.status_code == 404
        response_data = response.body.decode()
        import json
        parsed_response = json.loads(response_data)
        
        assert parsed_response["error_type"] == "TRANSCRIPT_NOT_AVAILABLE"
        assert "disabled by video creator" in parsed_response["message"]
        assert parsed_response["status_code"] == 404

    def test_invalid_response_error_response(self):
        """Test that InvalidResponseError returns proper structured response."""
        from mcp_server_youtube.utils.exception_handler import youtube_exception_handler
        from fastapi import Request
        
        request = Mock(spec=Request)
        request.url.path = "/search"
        request.method = "GET"
        request.headers.get.return_value = "test-agent"
        
        exc = InvalidResponseError("YouTube API returned malformed JSON")
        
        import asyncio
        response = asyncio.run(youtube_exception_handler(request, exc))
        
        assert response.status_code == 502
        response_data = response.body.decode()
        import json
        parsed_response = json.loads(response_data)
        
        assert parsed_response["error_type"] == "INVALID_YOUTUBE_RESPONSE"
        assert "malformed JSON" in parsed_response["message"]
        assert parsed_response["status_code"] == 502
