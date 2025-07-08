import pytest
from unittest.mock import Mock, patch, AsyncMock
from contextlib import asynccontextmanager

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from mcp_server_youtube.server import app_lifespan, youtube_search_and_transcript
from mcp_server_youtube.youtube import YouTubeClientError
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
        
        # Test
