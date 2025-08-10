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
    
    def test_retry_on_youtube_api_error_then_success(self, mock_youtube_searcher_sync, caplog):
        """Test retry triggered on YouTubeApiError, eventually succeeds."""
        # Use predefined mock response
        mock_response = MOCK_RESPONSES['video1']
        
        # Create HttpError instance that will be wrapped in YouTubeApiError
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
        
        # Set up mock chain for search().list().execute()
        mock_search = Mock()
        mock_list = Mock()
        mock_list.execute.side_effect = mock_execute
        mock_search.list.return_value = mock_list
        mock_youtube_searcher_sync.youtube_service.search.return_value = mock_search
        
        # Mock transcript fetching
        with patch.object(mock_youtube_searcher_sync, '_get_transcript_by_id') as mock_transcript:
            mock_transcript.return_value = ("Test transcript", "en", True)
            
            with caplog.at_level(logging.WARNING):
                result = mock_youtube_searcher_sync.search_videos("test query")
        
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
    
    def test_retry_on_youtube_client_error_then_success(self, mock_youtube_searcher_sync, caplog):
        """Test retry triggered on YouTubeClientError, eventually succeeds."""
        # Use predefined mock response
        mock_response = MOCK_RESPONSES['video2']
        
        # Mock YouTube service call: first throws generic Exception (wrapped in YouTubeClientError), second succeeds
        call_count = 0
        def mock_execute():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("Client connection failed")
            return mock_response
        
        # Set up mock chain
        mock_search = Mock()
        mock_list = Mock()
        mock_list.execute.side_effect = mock_execute
        mock_search.list.return_value = mock_list
        mock_youtube_searcher_sync.youtube_service.search.return_value = mock_search
        
        # Mock transcript fetching
        with patch.object(mock_youtube_searcher_sync, '_get_transcript_by_id') as mock_transcript:
            mock_transcript.return_value = ("Another transcript", "en", True)
            
            with caplog.at_level(logging.WARNING):
                result = mock_youtube_searcher_sync.search_videos("another test")
        
        # Verify results
        assert len(result) == 1
        assert result[0].video_id == TEST_VIDEO_IDS['video2']
        
        # Verify retry occurred
        assert call_count == 2
        
        # Verify retry logs
        retry_logs = [record for record in caplog.records if "Retrying" in record.message]
        assert len(retry_logs) == 1
        assert "YouTubeClientError" in retry_logs[0].message
    
    def test_max_retries_exceeded_for_search(self, mock_youtube_searcher_sync, caplog):
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
        mock_list.execute.side_effect = mock_execute
        mock_search.list.return_value = mock_list
        mock_youtube_searcher_sync.youtube_service.search.return_value = mock_search
        
        with caplog.at_level(logging.WARNING):
            with pytest.raises(YouTubeApiError):
                mock_youtube_searcher_sync.search_videos("failing query")
        
        # Verify retry count (5 retries = total 5 calls)
        assert call_count == 5
        
        # Verify retry logs (should have 4 retry logs)
        retry_logs = [record for record in caplog.records if "Retrying" in record.message]
        assert len(retry_logs) == 4
    
    # def test_no_retry_on_non_retryable_error(self, mock_youtube_searcher_sync, caplog):
    #     """[DEPRECATED] All exception of mock_youtube_searcher_sync.search_videos should be retried"""
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
    #     mock_youtube_searcher_sync.youtube_service.search.return_value = mock_search
        
    #     with caplog.at_level(logging.WARNING):
    #         with pytest.raises(YouTubeClientError):
    #             mock_youtube_searcher_sync.search_videos("invalid query")
        
    #     # Should only retry once
    #     assert call_count == 1
        
    #     # Should not retry log
    #     retry_logs = [record for record in caplog.records if "Retrying" in record.message]
    #     assert len(retry_logs) == 0


class TestRetryTranscriptApiDecorator:
    """Test the functionality of retry_transcript_api decorator."""
    
    def test_retry_on_transcript_error_then_success(self, mock_youtube_searcher_sync, caplog):
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
                result = mock_youtube_searcher_sync._get_transcript_by_id(TEST_VIDEO_IDS['video1'], "en")
        
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
    
    def test_retry_on_timeout_error_then_success(self, mock_youtube_searcher_sync, caplog):
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
                result = mock_youtube_searcher_sync._get_transcript_by_id(TEST_VIDEO_IDS['video2'], "en")
        
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
    
    def test_max_retries_exceeded_for_transcript(self, mock_youtube_searcher_sync, caplog):
        """Test transcript retry returns fallback value after exceeding max retries."""
        # Mock persistent failure
        def mock_fetch_side_effect(language):
            raise ConnectionError("Persistent connection error")
        
        with patch('mcp_server_youtube.youtube.module.TranscriptFetcher') as mock_fetcher_class:
            mock_fetcher = Mock()
            mock_fetcher.fetch.side_effect = mock_fetch_side_effect
            mock_fetcher_class.return_value = mock_fetcher
            
            with caplog.at_level(logging.WARNING):
                # With retry_error_callback, should return fallback value even with reraise=True
                result = mock_youtube_searcher_sync._get_transcript_by_id(TEST_VIDEO_IDS['video3'], "en")
        
        # Verify results (should return fallback value from callback)
        transcript, language, has_transcript = result
        assert transcript == "Transcript service temporarily unavailable"
        assert language is None
        assert has_transcript is False
        
        # Verify retry count (5 retries = total 5 calls)
        assert mock_fetcher.fetch.call_count == 5
        
        # Verify retry logs
        retry_logs = [record for record in caplog.records if "Retrying" in record.message]
        assert len(retry_logs) == 4  # 4 retry logs
    
    def test_exponential_backoff_timing(self, mock_youtube_searcher_sync):
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
            result = mock_youtube_searcher_sync._get_transcript_by_id(TEST_VIDEO_IDS['video1'], "en")
            end_time = time.time()
        
        # Verify results
        transcript, language, has_transcript = result
        assert transcript == "Final success"
        assert has_transcript is True
        
        # Verify total time (should have at least backoff delay: 0.5s + 1.0s = 1.5s)
        total_time = end_time - start_time
        assert total_time >= 1.5  # At least exponential backoff delay
        assert total_time < 5.0   # But should not be too long
    
    def test_retry_logging_details(self, mock_youtube_searcher_sync, caplog):
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
                result = mock_youtube_searcher_sync._get_transcript_by_id(TEST_VIDEO_IDS['video2'], "en")
        
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
    
    def test_search_with_transcript_retries(self, mock_youtube_searcher_sync, caplog):
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
        mock_youtube_searcher_sync.youtube_service.search.return_value = mock_search
        
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
                result = mock_youtube_searcher_sync.search_videos("integrated test")
        
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


class TestRetryDecoratorEdgeCases:
    """Test edge cases and additional scenarios for retry decorators."""
    
    def test_retry_with_different_http_error_codes(self, mock_youtube_searcher_sync, caplog):
        """Test retry behavior with different HTTP error codes."""
        mock_response = MOCK_RESPONSES['video1']
        
        # Test 503 (Service Unavailable) - should retry
        http_error_503 = HttpError(
            resp=Mock(status=503),
            content=b'{"error": {"message": "Service Unavailable"}}'
        )
        
        # Test 502 (Bad Gateway) - should retry
        http_error_502 = HttpError(
            resp=Mock(status=502),
            content=b'{"error": {"message": "Bad Gateway"}}'
        )
        
        call_count = 0
        def mock_execute():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise http_error_503
            elif call_count == 2:
                raise http_error_502
            return mock_response
        
        mock_search = Mock()
        mock_list = Mock()
        mock_list.execute.side_effect = mock_execute
        mock_search.list.return_value = mock_list
        mock_youtube_searcher_sync.youtube_service.search.return_value = mock_search
        
        with patch.object(mock_youtube_searcher_sync, '_get_transcript_by_id') as mock_transcript:
            mock_transcript.return_value = ("Test transcript", "en", True)
            
            with caplog.at_level(logging.WARNING):
                result = mock_youtube_searcher_sync.search_videos("test query")
        
        # Verify success after retries
        assert len(result) == 1
        assert call_count == 3
        
        # Verify both errors triggered retries
        retry_logs = [record for record in caplog.records if "Retrying" in record.message]
        assert len(retry_logs) == 2

    def test_transcript_retry_with_different_exceptions(self, mock_youtube_searcher_sync, caplog):
        """Test transcript retry with various exception types."""
        call_count = 0
        
        def mock_fetch_side_effect(language):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("Network connection failed")
            elif call_count == 2:
                raise TimeoutError("Request timeout")
            elif call_count == 3:
                raise OSError("OS level error")
            # Fourth time succeeds
            return TranscriptResult(
                status=TranscriptStatus.SUCCESS,
                transcript="Success after multiple retries",
                language="en",
                available_languages=["en"],
                error_message=None
            )
        
        with patch('mcp_server_youtube.youtube.module.TranscriptFetcher') as mock_fetcher_class:
            mock_fetcher = Mock()
            mock_fetcher.fetch.side_effect = mock_fetch_side_effect
            mock_fetcher_class.return_value = mock_fetcher
            
            with caplog.at_level(logging.WARNING):
                result = mock_youtube_searcher_sync._get_transcript_by_id(TEST_VIDEO_IDS['video1'], "en")
        
        # Verify results
        transcript, language, has_transcript = result
        assert transcript == "Success after multiple retries"
        assert has_transcript is True
        assert call_count == 4
        
        # Verify all three error types triggered retries
        retry_logs = [record for record in caplog.records if "Retrying" in record.message]
        assert len(retry_logs) == 3
        assert "ConnectionError" in retry_logs[0].message
        assert "TimeoutError" in retry_logs[1].message
        assert "OSError" in retry_logs[2].message

    def test_search_no_retry_on_successful_first_attempt(self, mock_youtube_searcher_sync, caplog):
        """Test that successful search doesn't trigger any retries."""
        mock_response = MOCK_RESPONSES['video1']
        
        call_count = 0
        def mock_execute():
            nonlocal call_count
            call_count += 1
            return mock_response
        
        mock_search = Mock()
        mock_list = Mock()
        mock_list.execute.side_effect = mock_execute
        mock_search.list.return_value = mock_list
        mock_youtube_searcher_sync.youtube_service.search.return_value = mock_search
        
        with patch.object(mock_youtube_searcher_sync, '_get_transcript_by_id') as mock_transcript:
            mock_transcript.return_value = ("Test transcript", "en", True)
            
            with caplog.at_level(logging.WARNING):
                result = mock_youtube_searcher_sync.search_videos("test query")
        
        # Verify success on first try
        assert len(result) == 1
        assert call_count == 1
        
        # Verify no retry logs
        retry_logs = [record for record in caplog.records if "Retrying" in record.message]
        assert len(retry_logs) == 0

    def test_transcript_no_retry_on_successful_first_attempt(self, mock_youtube_searcher_sync, caplog):
        """Test that successful transcript fetch doesn't trigger any retries."""
        call_count = 0
        
        def mock_fetch_side_effect(language):
            nonlocal call_count
            call_count += 1
            return TranscriptResult(
                status=TranscriptStatus.SUCCESS,
                transcript="Immediate success",
                language="en",
                available_languages=["en"],
                error_message=None
            )
        
        with patch('mcp_server_youtube.youtube.module.TranscriptFetcher') as mock_fetcher_class:
            mock_fetcher = Mock()
            mock_fetcher.fetch.side_effect = mock_fetch_side_effect
            mock_fetcher_class.return_value = mock_fetcher
            
            with caplog.at_level(logging.WARNING):
                result = mock_youtube_searcher_sync._get_transcript_by_id(TEST_VIDEO_IDS['video1'], "en")
        
        # Verify success on first try
        transcript, language, has_transcript = result
        assert transcript == "Immediate success"
        assert has_transcript is True
        assert call_count == 1
        
        # Verify no retry logs
        retry_logs = [record for record in caplog.records if "Retrying" in record.message]
        assert len(retry_logs) == 0