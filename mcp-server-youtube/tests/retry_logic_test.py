"""Test cases for retry mechanism.

Test the functionality of retry_search and retry_transcript_api decorators,
including retry triggering, retry count, exponential backoff timing and logging.
"""
import logging
import time
from unittest.mock import Mock, patch
import pytest
from googleapiclient.errors import HttpError
from mcp_server_youtube.youtube.config import YouTubeConfig
from mcp_server_youtube.youtube.module import YouTubeSearcher
from mcp_server_youtube.youtube.youtube_errors import YouTubeApiError, YouTubeClientError
from mcp_server_youtube.youtube.models import TranscriptStatus, TranscriptResult


# Test data constants
TEST_VIDEO_IDS = {
    'video1': 'dQw4w9WgXcQ',
    'video2': 'jNQXAC9IVRw', 
    'video3': 'ScMzIvxBSi4'
}

MOCK_RESPONSES = {
    'video1': {
        'items': [{
            'id': {'kind': 'youtube#video', 'videoId': TEST_VIDEO_IDS['video1']},
            'snippet': {
                'title': 'Test Video',
                'description': 'Test Description',
                'channelTitle': 'Test Channel',
                'publishedAt': '2023-01-01T00:00:00Z',
                'thumbnails': {'default': {'url': 'http://test.jpg'}}
            }
        }]
    },
    'video2': {
        'items': [{
            'id': {'kind': 'youtube#video', 'videoId': TEST_VIDEO_IDS['video2']},
            'snippet': {
                'title': 'Another Test Video',
                'description': 'Another Description',
                'channelTitle': 'Another Channel',
                'publishedAt': '2023-01-02T00:00:00Z',
                'thumbnails': {'default': {'url': 'http://test2.jpg'}}
            }
        }]
    },
    'video3': {
        'items': [{
            'id': {'kind': 'youtube#video', 'videoId': TEST_VIDEO_IDS['video3']},
            'snippet': {
                'title': 'Integrated Test Video',
                'description': 'Test Description',
                'channelTitle': 'Test Channel',
                'publishedAt': '2023-01-01T00:00:00Z',
                'thumbnails': {'default': {'url': 'http://test.jpg'}}
            }
        }]
    }
}


class TestRetrySearchDecorator:
    """Test the functionality of retry_search decorator."""
    
    @pytest.fixture
    def youtube_searcher(self):
        """Create YouTubeSearcher instance for testing."""
        config = YouTubeConfig()
        with patch.object(config, 'api_key', 'test_api_key'):
            with patch('mcp_server_youtube.youtube.module.build') as mock_build:
                mock_service = Mock()
                mock_build.return_value = mock_service
                searcher = YouTubeSearcher(config)
                return searcher
    
    def test_retry_on_youtube_api_error_then_success(self, youtube_searcher, caplog):
        """Test retry triggered on YouTubeApiError, eventually succeeds."""
        # Use predefined mock response
        mock_response = MOCK_RESPONSES['video1']
        
        # Create HttpError instance
        http_error = HttpError(
            resp=Mock(status=503),
            content=b'{"error": {"message": "Service Unavailable"}}'
        )
        
        # Mock YouTube service call count
        call_count = 0
        def mock_execute():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise http_error
            return mock_response
        
        # Set up mock chain
        mock_search = Mock()
        mock_list = Mock()
        mock_execute = Mock(side_effect=mock_execute)
        mock_list.execute = mock_execute
        mock_search.list.return_value = mock_list
        youtube_searcher.youtube_service.search.return_value = mock_search
        
        # Mock transcript fetching
        with patch.object(youtube_searcher, '_get_transcript_by_id') as mock_transcript:
            mock_transcript.return_value = ("Test transcript", "en", True)
            
            with caplog.at_level(logging.WARNING):
                result = youtube_searcher.search_videos("test query")
        
        # Verify results
        assert len(result) == 1
        assert result[0].video_id == TEST_VIDEO_IDS['video1']
        assert result[0].title == 'Test Video'
        
        # Verify retry count (should call 3 times)
        assert call_count == 3
        
        # Verify retry logs
        retry_logs = [record for record in caplog.records if "Retrying" in record.message]
        assert len(retry_logs) == 2  # Two retry logs
        assert "search_videos" in retry_logs[0].message
        assert "YouTubeApiError" in retry_logs[0].message
    
    def test_retry_on_youtube_client_error_then_success(self, youtube_searcher, caplog):
        """Test retry triggered on YouTubeClientError, eventually succeeds."""
        # Use predefined mock response
        mock_response = MOCK_RESPONSES['video2']
        
        # Mock YouTube service call: first throws YouTubeClientError, second succeeds
        call_count = 0
        def mock_execute():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise YouTubeClientError("Client initialization failed")
            return mock_response
        
        # Set up mock chain
        mock_search = Mock()
        mock_list = Mock()
        mock_execute = Mock(side_effect=mock_execute)
        mock_list.execute = mock_execute
        mock_search.list.return_value = mock_list
        youtube_searcher.youtube_service.search.return_value = mock_search
        
        # Mock transcript fetching
        with patch.object(youtube_searcher, '_get_transcript_by_id') as mock_transcript:
            mock_transcript.return_value = ("Another transcript", "en", True)
            
            with caplog.at_level(logging.WARNING):
                result = youtube_searcher.search_videos("another test")
        
        # Verify results
        assert len(result) == 1
        assert result[0].video_id == TEST_VIDEO_IDS['video2']
        
        # Verify retry occurred
        assert call_count == 2
        
        # Verify retry logs
        retry_logs = [record for record in caplog.records if "Retrying" in record.message]
        assert len(retry_logs) == 1
        assert "YouTubeClientError" in retry_logs[0].message
    
    def test_max_retries_exceeded_for_search(self, youtube_searcher, caplog):
        """Test that search throws exception after exceeding max retries."""
        # Mock persistent failing HttpError
        http_error = HttpError(
            resp=Mock(status=500),
            content=b'{"error": {"message": "Internal Server Error"}}'
        )
        
        call_count = 0
        def mock_execute():
            nonlocal call_count
            call_count += 1
            raise http_error
        
        mock_search = Mock()
        mock_list = Mock()
        mock_execute = Mock(side_effect=mock_execute)
        mock_list.execute = mock_execute
        mock_search.list.return_value = mock_list
        youtube_searcher.youtube_service.search.return_value = mock_search
        
        with caplog.at_level(logging.WARNING):
            with pytest.raises(YouTubeApiError):
                youtube_searcher.search_videos("failing query")
        
        # Verify retry count (5 retries = total 5 calls)
        assert call_count == 5
        
        # Verify retry logs (should have 4 retry logs)
        retry_logs = [record for record in caplog.records if "Retrying" in record.message]
        assert len(retry_logs) == 4
    
    # def test_no_retry_on_non_retryable_error(self, youtube_searcher, caplog):
    #     """[DEPRECATED] All exception of youtube_searcher.search_videos should be retried"""
    #     # Mock error
    #     call_count = 0
    #     def mock_execute():
    #         nonlocal call_count
    #         call_count += 1
    #         raise ValueError("Invalid parameter")
        
    #     mock_search = Mock()
    #     mock_list = Mock()
    #     mock_execute = Mock(side_effect=mock_execute)
    #     mock_list.execute = mock_execute
    #     mock_search.list.return_value = mock_list
    #     youtube_searcher.youtube_service.search.return_value = mock_search
        
    #     with caplog.at_level(logging.WARNING):
    #         with pytest.raises(YouTubeClientError):
    #             youtube_searcher.search_videos("invalid query")
        
    #     # Should only retry once
    #     assert call_count == 1
        
    #     # Should not retry log
    #     retry_logs = [record for record in caplog.records if "Retrying" in record.message]
    #     assert len(retry_logs) == 0


class TestRetryTranscriptApiDecorator:
    """Test the functionality of retry_transcript_api decorator."""
    
    @pytest.fixture
    def youtube_searcher(self):
        """Create YouTubeSearcher instance for testing."""
        config = YouTubeConfig()
        with patch.object(config, 'api_key', 'test_api_key'):
            with patch('mcp_server_youtube.youtube.module.build'):
                searcher = YouTubeSearcher(config)
                return searcher

    def test_retry_on_transcript_error_then_success(self, youtube_searcher, caplog):
        """Test transcript fetching triggers retry on exception, eventually succeeds."""
        # Mock TranscriptFetcher behavior
        call_count = 0
        
        def mock_fetch_side_effect(language):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                # First two times throw exception
                raise ConnectionError("Network connection failed")
            # Third time succeeds
            return TranscriptResult(
                status=TranscriptStatus.SUCCESS,
                transcript="Test transcript content",
                language="en",
                available_languages=["en"],
                error_message=None
            )
        
        with patch('mcp_server_youtube.youtube.module.TranscriptFetcher') as mock_fetcher_class:
            mock_fetcher = Mock()
            mock_fetcher.fetch.side_effect = mock_fetch_side_effect
            mock_fetcher_class.return_value = mock_fetcher
            
            with caplog.at_level(logging.WARNING):
                result = youtube_searcher._get_transcript_by_id(TEST_VIDEO_IDS['video1'], "en")
        
        # Verify results
        transcript, language, has_transcript = result
        assert transcript == "Test transcript content"
        assert language == "en"
        assert has_transcript is True
        
        # Verify retry count
        assert call_count == 3
        
        # Verify retry logs
        retry_logs = [record for record in caplog.records if "Retrying" in record.message]
        assert len(retry_logs) == 2  # Two retry logs
        assert "_get_transcript_by_id" in retry_logs[0].message
    
    def test_retry_on_timeout_error_then_success(self, youtube_searcher, caplog):
        """Test transcript fetching triggers retry on timeout error, eventually succeeds."""
        call_count = 0
        
        def mock_fetch_side_effect(language):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise TimeoutError("Request timeout")
            return TranscriptResult(
                status=TranscriptStatus.SUCCESS,
                transcript="Recovered transcript",
                language="en",
                available_languages=["en"],
                error_message=None
            )
        
        with patch('mcp_server_youtube.youtube.module.TranscriptFetcher') as mock_fetcher_class:
            mock_fetcher = Mock()
            mock_fetcher.fetch.side_effect = mock_fetch_side_effect
            mock_fetcher_class.return_value = mock_fetcher
            
            with caplog.at_level(logging.WARNING):
                result = youtube_searcher._get_transcript_by_id(TEST_VIDEO_IDS['video2'], "en")
        
        # Verify results
        transcript, language, has_transcript = result
        assert transcript == "Recovered transcript"
        assert has_transcript is True
        
        # Verify retry count
        assert call_count == 2
        
        # Verify retry logs
        retry_logs = [record for record in caplog.records if "Retrying" in record.message]
        assert len(retry_logs) == 1
        assert "TimeoutError" in retry_logs[0].message
    
    def test_max_retries_exceeded_for_transcript(self, youtube_searcher, caplog):
        """Test transcript retry returns error status after exceeding max retries."""
        # Mock persistent failure
        def mock_fetch_side_effect(language):
            raise ConnectionError("Persistent connection error")
        
        with patch('mcp_server_youtube.youtube.module.TranscriptFetcher') as mock_fetcher_class:
            mock_fetcher = Mock()
            mock_fetcher.fetch.side_effect = mock_fetch_side_effect
            mock_fetcher_class.return_value = mock_fetcher
            
            with caplog.at_level(logging.WARNING):
                result = youtube_searcher._get_transcript_by_id(TEST_VIDEO_IDS['video3'], "en")
        
        # Verify results (should return error status instead of throwing exception)
        transcript, language, has_transcript = result
        assert "Transcript service temporarily unavailable" in transcript
        assert language is None
        assert has_transcript is False
        
        # Verify retry count (5 retries = total 5 calls)
        assert mock_fetcher.fetch.call_count == 5
        
        # Verify retry logs
        retry_logs = [record for record in caplog.records if "Retrying" in record.message]
        assert len(retry_logs) == 4  # 4 retry logs
    
    def test_exponential_backoff_timing(self, youtube_searcher):
        """Test exponential backoff timing."""
        call_count = 0
        
        def mock_fetch_side_effect(language):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise ConnectionError("Network error")
            return TranscriptResult(
                status=TranscriptStatus.SUCCESS,
                transcript="Final success",
                language="en",
                available_languages=["en"],
                error_message=None
            )
        
        with patch('mcp_server_youtube.youtube.module.TranscriptFetcher') as mock_fetcher_class:
            mock_fetcher = Mock()
            mock_fetcher.fetch.side_effect = mock_fetch_side_effect
            mock_fetcher_class.return_value = mock_fetcher
            
            start_time = time.time()
            result = youtube_searcher._get_transcript_by_id(TEST_VIDEO_IDS['video1'], "en")
            end_time = time.time()
        
        # Verify results
        transcript, language, has_transcript = result
        assert transcript == "Final success"
        assert has_transcript is True
        
        # Verify total time (should have at least backoff delay: 0.5s + 1.0s = 1.5s)
        total_time = end_time - start_time
        assert total_time >= 1.5  # At least exponential backoff delay
        assert total_time < 5.0   # But should not be too long
    
    def test_retry_logging_details(self, youtube_searcher, caplog):
        """Test detailed content of retry logs."""
        call_count = 0
        
        def mock_fetch_side_effect(language):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("First connection error")
            elif call_count == 2:
                raise TimeoutError("Request timeout")
            return TranscriptResult(
                status=TranscriptStatus.SUCCESS,
                transcript="Success after retries",
                language="en",
                available_languages=["en"],
                error_message=None
            )
        
        with patch('mcp_server_youtube.youtube.module.TranscriptFetcher') as mock_fetcher_class:
            mock_fetcher = Mock()
            mock_fetcher.fetch.side_effect = mock_fetch_side_effect
            mock_fetcher_class.return_value = mock_fetcher
            
            with caplog.at_level(logging.WARNING):
                result = youtube_searcher._get_transcript_by_id(TEST_VIDEO_IDS['video2'], "en")
        
        # Verify results
        transcript, language, has_transcript = result
        assert transcript == "Success after retries"
        
        # Verify detailed content of retry logs
        retry_logs = [record for record in caplog.records if "Retrying" in record.message]
        assert len(retry_logs) == 2
        
        # First retry log should contain ConnectionError
        assert "_get_transcript_by_id" in retry_logs[0].message
        assert "ConnectionError" in retry_logs[0].message
        assert "0.5 seconds" in retry_logs[0].message
        
        # Second retry log should contain TimeoutError
        assert "_get_transcript_by_id" in retry_logs[1].message
        assert "TimeoutError" in retry_logs[1].message
        assert "1.0 seconds" in retry_logs[1].message or "1 second" in retry_logs[1].message


class TestIntegratedRetryBehavior:
    """Test integrated retry behavior."""
    
    @pytest.fixture
    def youtube_searcher(self):
        """Create YouTubeSearcher instance for testing."""
        config = YouTubeConfig()
        with patch.object(config, 'api_key', 'test_api_key'):
            with patch('mcp_server_youtube.youtube.module.build') as mock_build:
                mock_service = Mock()
                mock_build.return_value = mock_service
                searcher = YouTubeSearcher(config)
                return searcher
    
    def test_search_with_transcript_retries(self, youtube_searcher, caplog):
        """Test integrated scenario where both search and transcript have retries."""
        # Use predefined mock response
        mock_response = MOCK_RESPONSES['video3']
        
        # Mock search: first fails, second succeeds
        http_error = HttpError(
            resp=Mock(status=503),
            content=b'{"error": {"message": "Service Unavailable"}}'
        )
        
        search_call_count = 0
        def mock_execute():
            nonlocal search_call_count
            search_call_count += 1
            if search_call_count == 1:
                raise http_error
            return mock_response
        
        mock_search = Mock()
        mock_list = Mock()
        mock_execute = Mock(side_effect=mock_execute)
        mock_list.execute = mock_execute
        mock_search.list.return_value = mock_list
        youtube_searcher.youtube_service.search.return_value = mock_search
        
        # Mock transcript: first fails, second succeeds
        transcript_call_count = 0
        
        def mock_transcript_fetch(language):
            nonlocal transcript_call_count
            transcript_call_count += 1
            if transcript_call_count == 1:
                raise ConnectionError("Transcript connection failed")
            return TranscriptResult(
                status=TranscriptStatus.SUCCESS,
                transcript="Integrated test transcript",
                language="en",
                available_languages=["en"],
                error_message=None
            )
        
        with patch('mcp_server_youtube.youtube.module.TranscriptFetcher') as mock_fetcher_class:
            mock_fetcher = Mock()
            mock_fetcher.fetch.side_effect = mock_transcript_fetch
            mock_fetcher_class.return_value = mock_fetcher
            
            with caplog.at_level(logging.WARNING):
                result = youtube_searcher.search_videos("integrated test")
        
        # Verify results
        assert len(result) == 1
        assert result[0].video_id == TEST_VIDEO_IDS['video3']
        assert result[0].transcript == "Integrated test transcript"
        assert result[0].has_transcript is True
        
        # Verify search retry
        assert search_call_count == 2
        
        # Verify transcript retry
        assert transcript_call_count == 2
        
        # Verify retry logs (search 1 time + transcript 1 time)
        retry_logs = [record for record in caplog.records if "Retrying" in record.message]
        assert len(retry_logs) == 2
        
        # Verify log content
        search_retry_logs = [log for log in retry_logs if "search_videos" in log.message]
        transcript_retry_logs = [log for log in retry_logs if "_get_transcript_by_id" in log.message]
        
        assert len(search_retry_logs) == 1
        assert len(transcript_retry_logs) == 1
        assert "YouTubeApiError" in search_retry_logs[0].message
        assert "ConnectionError" in transcript_retry_logs[0].message