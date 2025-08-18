import pytest
import json
from unittest.mock import Mock, patch, AsyncMock


from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from pydantic import ValidationError as PydanticValidationError

from mcp_server_youtube.server import app_lifespan, youtube_search_and_transcript, ValidationError
from mcp_server_youtube.youtube.youtube_errors import YouTubeClientError
from mcp_server_youtube.youtube.models import YouTubeSearchRequest, YouTubeSearchResponse



class TestAppLifespan:
    """Test cases for app_lifespan context manager."""

    @pytest.mark.asyncio
    async def test_app_lifespan_success(self, mock_context):
        """Test successful app lifespan initialization."""
        mock_server = Mock(spec=FastMCP)
        mock_searcher = Mock()

        with patch(
            "mcp_server_youtube.server.get_youtube_searcher"
        ) as mock_get_searcher:
            mock_get_searcher.return_value = mock_searcher

            async with app_lifespan(mock_server) as context:
                assert "youtube_searcher" in context
                assert context["youtube_searcher"] is mock_searcher

            mock_get_searcher.assert_called_once()

    @pytest.mark.asyncio
    async def test_app_lifespan_youtube_client_error(self, mock_context):
        """Test app lifespan with YouTubeClientError during initialization."""
        mock_server = Mock(spec=FastMCP)

        with patch(
            "mcp_server_youtube.server.get_youtube_searcher"
        ) as mock_get_searcher:
            mock_get_searcher.side_effect = YouTubeClientError("API key invalid")
            
            with pytest.raises(ToolError, match="Service initialization failed"):

                async with app_lifespan(mock_server):
                    pass

    @pytest.mark.asyncio
    async def test_app_lifespan_unexpected_error(self, mock_context):
        """Test app lifespan with unexpected error during initialization."""
        mock_server = Mock(spec=FastMCP)

        with patch(
            "mcp_server_youtube.server.get_youtube_searcher"
        ) as mock_get_searcher:
            mock_get_searcher.side_effect = Exception("Unexpected initialization error")
            
            with pytest.raises(ToolError, match="Unexpected startup error"):

                async with app_lifespan(mock_server):
                    pass


class TestYouTubeSearchAndTranscript:
    """Test cases for youtube_search_and_transcript tool."""

    @pytest.mark.asyncio
    async def test_youtube_search_and_transcript_success(self, sample_youtube_video, mock_context):
        """Test successful YouTube search and transcript retrieval."""
        # Get the mock searcher from the context
        mock_searcher = mock_context.lifespan_context['youtube_searcher']
        mock_searcher.search_videos.return_value = [sample_youtube_video]
        
        request = {
            "query": "test query",
            "max_results": 1,
            "transcript_language": "en"
        }
        
        result = await youtube_search_and_transcript.fn(ctx=mock_context, request=request)

        # Verify the searcher was called correctly
        mock_searcher.search_videos.assert_called_once_with(
            query="test query", max_results=1, language="en"
        )
        
        # Parse and verify the JSON result
        result_data = json.loads(result)
        assert "results" in result_data
        assert "total_results" in result_data
        assert result_data["total_results"] == 1
        assert len(result_data["results"]) == 1
        
        video_result = result_data["results"][0]
        assert video_result["video_id"] == sample_youtube_video.video_id
        assert video_result["title"] == sample_youtube_video.title


    @pytest.mark.asyncio
    async def test_youtube_search_and_transcript_multiple_videos(self, sample_youtube_video_1, sample_youtube_video_2, mock_context):
        """Test YouTube search returning multiple videos."""
        # Get the mock searcher from the context
        mock_searcher = mock_context.lifespan_context['youtube_searcher']
        mock_searcher.search_videos.return_value = [sample_youtube_video_1, sample_youtube_video_2]
        
        request = {
            "query": "test query",
            "max_results": 2
        }
        
        result = await youtube_search_and_transcript.fn(ctx=mock_context, request=request)
        
        # Parse and verify the JSON result
        result_data = json.loads(result)
        assert result_data["total_results"] == 2
        assert len(result_data["results"]) == 2
        
        # Verify both videos are in the result
        video_ids = [video["video_id"] for video in result_data["results"]]
        assert "dQw4w9WgXcQ" in video_ids
        assert "ScMzIvxBSi4" in video_ids

    @pytest.mark.asyncio
    async def test_youtube_search_and_transcript_default_params(self, mock_context):
        """Test YouTube search with default parameters."""
        mock_searcher = mock_context.lifespan_context["youtube_searcher"]
        mock_searcher.search_videos.return_value = []
        
        request = {"query": "test query"}
        
        await youtube_search_and_transcript.fn(ctx=mock_context, request=request)
        
        # Verify default parameters are used
        mock_searcher.search_videos.assert_called_once_with(
            query="test query",
            max_results=5,  # Default value from YouTubeSearchRequest
            language="en"   # Default value when transcript_language is None

        )

    @pytest.mark.asyncio
    async def test_youtube_search_and_transcript_custom_params(self, mock_context):
        """Test YouTube search with custom parameters."""
        # Get searcher from mock_context
        mock_searcher = mock_context.lifespan_context["youtube_searcher"]
        mock_searcher.search_videos.return_value = []
        
        request = {
            "query": "custom query",
            "max_results": 5,
            "transcript_language": "es"
        }
        
        await youtube_search_and_transcript.fn(ctx=mock_context, request=request)
        

        mock_searcher.search_videos.assert_called_once_with(
            query="custom query", max_results=5, language="es"
        )

    @pytest.mark.asyncio
    async def test_youtube_search_and_transcript_empty_results(self, mock_context):
        """Test YouTube search returning no results."""
        # Get searcher from mock_context
        mock_searcher = mock_context.lifespan_context["youtube_searcher"]
        mock_searcher.search_videos.return_value = []
        
        request = {"query": "nonexistent"}
        
        result = await youtube_search_and_transcript.fn(ctx=mock_context, request=request)
        
        # Parse and verify the JSON result for empty results
        result_data = json.loads(result)
        assert result_data["total_results"] == 0
        assert result_data["results"] == []


    @pytest.mark.asyncio
    async def test_youtube_search_and_transcript_youtube_client_error(self, mock_context):
        """Test handling of YouTubeClientError."""
        # Get searcher from mock_context
        mock_searcher = mock_context.lifespan_context["youtube_searcher"]
        mock_searcher.search_videos.side_effect = YouTubeClientError("API quota exceeded")
        
        request = {"query": "test query"}
        
        with pytest.raises(ToolError, match="YouTube API error: API quota exceeded"):
            await youtube_search_and_transcript.fn(ctx=mock_context, request=request)


    @pytest.mark.asyncio
    async def test_youtube_search_and_transcript_unexpected_error(self, mock_context):
        """Test handling of unexpected errors."""
        # Get searcher from mock_context
        mock_searcher = mock_context.lifespan_context["youtube_searcher"]
        mock_searcher.search_videos.side_effect = Exception("Unexpected error")
        
        request = {"query": "test query"}
        
        with pytest.raises(ToolError, match="Internal error: Unexpected error"):
            await youtube_search_and_transcript.fn(ctx=mock_context, request=request)


    @pytest.mark.asyncio
    async def test_youtube_search_and_transcript_validation_error(self, mock_context):
        """Test parameter validation errors."""
        # Get searcher from mock_context
        mock_searcher = mock_context.lifespan_context["youtube_searcher"]
        mock_searcher.search_videos.return_value = []
        
        # Test with invalid max_results (negative number)
        invalid_request = {
            "query": "test",
            "max_results": -1
        }
        
        with pytest.raises(ValidationError):
            await youtube_search_and_transcript.fn(ctx=mock_context, request=invalid_request)

    @pytest.mark.asyncio
    async def test_youtube_search_and_transcript_missing_required_field(self, mock_context):
        """Test handling of missing required fields."""
        # Get searcher from mock_context
        mock_searcher = mock_context.lifespan_context["youtube_searcher"]
        
        # Test with missing query field
        invalid_request = {
            "max_results": 5
        }
        
        with pytest.raises(ValidationError):
            await youtube_search_and_transcript.fn(ctx=mock_context, request=invalid_request)

    @pytest.mark.asyncio
    async def test_youtube_search_and_transcript_context_access(self, mock_context):
        """Test proper context access and lifespan context retrieval."""
        # Test with missing lifespan context
        empty_context = Mock()
        empty_context.lifespan_context = {}
        
        request = {"query": "test"}
        
        with pytest.raises(KeyError):
            await youtube_search_and_transcript.fn(ctx=empty_context, request=request)

    @pytest.mark.asyncio
    async def test_youtube_search_and_transcript_with_transcript_language_none(self, mock_context):
        """Test YouTube search with None transcript_language defaults to 'en'."""
        # Get searcher from mock_context
        mock_searcher = mock_context.lifespan_context["youtube_searcher"]
        mock_searcher.search_videos.return_value = []
        
        request = {
            "query": "test query",
            "transcript_language": None
        }
        
        await youtube_search_and_transcript.fn(ctx=mock_context, request=request)
        
        # Verify that None transcript_language defaults to "en"
        mock_searcher.search_videos.assert_called_once_with(
            query="test query",
            max_results=5,
            language="en"
        )

    @pytest.mark.asyncio
    async def test_youtube_search_and_transcript_json_response_format(self, sample_youtube_video_for_json_test, mock_context):
        """Test that the response is properly formatted JSON."""
        mock_searcher = mock_context.lifespan_context["youtube_searcher"]
        mock_searcher.search_videos.return_value = [sample_youtube_video_for_json_test]
        
        request = {"query": "test query"}
        
        result = await youtube_search_and_transcript.fn(ctx=mock_context, request=request)
        
        # Verify it's valid JSON
        result_data = json.loads(result)
        
        # Verify the structure matches YouTubeSearchResponse
        assert "results" in result_data
        assert "total_results" in result_data
        assert isinstance(result_data["results"], list)
        assert isinstance(result_data["total_results"], int)
        
        # Verify video data structure
        video_data = result_data["results"][0]
        expected_fields = ["video_id", "title", "channel", "published_at", "thumbnail", "description", "transcript"]
        for field in expected_fields:
            assert field in video_data


class TestValidationError:
    """Test cases for ValidationError exception."""

    def test_validation_error_creation(self):
        """Test ValidationError creation with default and custom codes."""
        # Test with default code
        error = ValidationError("Test message")
        assert str(error) == "Test message"
        assert error.code == "VALIDATION_ERROR"
        
        # Test with custom code
        error = ValidationError("Test message", "CUSTOM_CODE")
        assert str(error) == "Test message"
        assert error.code == "CUSTOM_CODE"

    def test_validation_error_inheritance(self):
        """Test that ValidationError properly inherits from ToolError."""
        error = ValidationError("Test message")
        assert isinstance(error, ToolError)
        assert error.status_code == 400


class TestServerConfiguration:
    """Test cases for server configuration and setup."""
    
    def test_app_configuration(self):
        """Test that FastAPI app is properly configured."""
        from mcp_server_youtube.server import app
        
        assert app.title == "YouTube Search and Transcript API"
        assert app.version == "1.0.0"
        assert "name" in app.contact
        assert app.contact["name"] == "Xyber Labs"
        
    def test_cors_middleware_configuration(self):
        """Test that CORS middleware is properly configured."""
        from mcp_server_youtube.server import app
        
        # Check that CORS middleware is added
        cors_middleware = None
        for middleware in app.user_middleware:
            if middleware.cls.__name__ == "CORSMiddleware":
                cors_middleware = middleware
                break
                
        assert cors_middleware is not None, "CORS middleware should be configured"
        
    def test_mcp_server_initialization(self):
        """Test that MCP server is properly initialized."""
        from mcp_server_youtube.server import mcp_server
        
        assert mcp_server is not None
        assert hasattr(mcp_server, 'tool')
        
    def test_router_inclusion(self):
        """Test that router is included in the app."""
        from mcp_server_youtube.server import app
        
        # Check that routes are included
        assert len(app.routes) > 0


class TestParameterValidationEdgeCases:
    """Test cases for edge cases in parameter validation."""
    
    @pytest.mark.asyncio
    async def test_empty_query_handling(self, mock_context):
        """Test handling of empty query string."""
        # Get searcher from mock_context
        mock_searcher = mock_context.lifespan_context["youtube_searcher"]
        mock_searcher.search_videos.return_value = []
        
        # Empty string should be valid (minimum length is 1 in the model)
        request = {"query": "a"}  # Minimum valid query
        
        result = await youtube_search_and_transcript.fn(ctx=mock_context, request=request)
        
        result_data = json.loads(result)
        assert result_data["total_results"] == 0
        
    @pytest.mark.asyncio  
    async def test_maximum_results_boundary(self, mock_context):
        """Test boundary values for max_results."""
        # Get searcher from mock_context
        mock_searcher = mock_context.lifespan_context["youtube_searcher"]
        mock_searcher.search_videos.return_value = []
        
        # Test maximum allowed value
        request = {
            "query": "test",
            "max_results": 20  # Maximum allowed
        }
        
        await youtube_search_and_transcript.fn(ctx=mock_context, request=request)
        
        mock_searcher.search_videos.assert_called_once_with(
            query="test",
            max_results=20,
            language="en"
        )
        
    @pytest.mark.asyncio
    async def test_minimum_results_boundary(self, mock_context):
        """Test minimum boundary for max_results."""
        # Get searcher from mock_context
        mock_searcher = mock_context.lifespan_context["youtube_searcher"]
        mock_searcher.search_videos.return_value = []
        
        # Test minimum allowed value
        request = {
            "query": "test",
            "max_results": 1  # Minimum allowed
        }
        
        await youtube_search_and_transcript.fn(ctx=mock_context, request=request)
        
        mock_searcher.search_videos.assert_called_once_with(
            query="test",
            max_results=1,
            language="en"

        )
        
    @pytest.mark.asyncio
    async def test_various_transcript_languages(self, mock_context):
        """Test different transcript language codes."""
        # Get searcher from mock_context
        mock_searcher = mock_context.lifespan_context["youtube_searcher"]
        mock_searcher.search_videos.return_value = []
        
        language_codes = ["en", "es", "fr", "de", "ja", "ko"]
        
        for lang in language_codes:
            mock_searcher.reset_mock()
            request = {
                "query": "test",
                "transcript_language": lang
            }
            
            await youtube_search_and_transcript.fn(ctx=mock_context, request=request)
            
            mock_searcher.search_videos.assert_called_once_with(
                query="test",
                max_results=5,
                language=lang
            )

