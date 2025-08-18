import pytest
from unittest.mock import Mock, AsyncMock, patch

from fastapi.testclient import TestClient
from mcp_server_youtube.server import app

from mcp_server_youtube.youtube.config import YouTubeConfig
from mcp_server_youtube.youtube.models import YouTubeVideo


@pytest.fixture(autouse=True)
def fast_tests():
    """Make tests run faster by removing retry delays."""
    # Patch tenacity delays to be zero
    with patch('tenacity.wait_exponential', return_value=lambda retry_state: 0), \
         patch('tenacity.stop_after_attempt', return_value=lambda retry_state: True), \
         patch('tenacity.wait.wait_exponential', return_value=lambda retry_state: 0):
        yield


@pytest.fixture(autouse=True)
def clear_caches():
    """Clear LRU caches between tests for consistent behavior."""
    yield
    # Clear caches after each test
    try:
        from mcp_server_youtube.youtube.module import get_youtube_searcher
        get_youtube_searcher.cache_clear()
    except (ImportError, AttributeError):
        pass  # Cache might not exist or be accessible


@pytest.fixture
def test_client():
    """FastAPI TestClient for HTTP API testing."""
    return TestClient(app)


@pytest.fixture
def api_endpoints():
    """Common API endpoint URLs for testing."""
    return {
        'search_and_transcript': '/youtube_search_and_transcript',
        'health': '/health'
    }


@pytest.fixture
def sample_search_request():
    """Sample valid search request for testing."""
    return {
        'request': {
            'query': 'python programming',
            'max_results': 5,
            'transcript_language': 'en'
        }
    }


@pytest.fixture
def sample_minimal_request():
    """Minimal valid search request for testing."""
    return {
        'request': {
            'query': 'python tutorial',
            'max_results': 3
        }
    }


@pytest.fixture
def invalid_requests():
    """Collection of invalid requests for validation testing."""
    return {
        'empty_query': {
            'request': {
                'query': '',
                'max_results': 5
            }
        },
        'whitespace_query': {
            'request': {
                'query': '   ',
                'max_results': 5
            }
        },
        'invalid_max_results_zero': {
            'request': {
                'query': 'test',
                'max_results': 0
            }
        },
        'invalid_max_results_high': {
            'request': {
                'query': 'test',
                'max_results': 25
            }
        },
        'invalid_language': {
            'request': {
                'query': 'test',
                'max_results': 5,
                'transcript_language': 'xyz'
            }
        },
        'invalid_date_format': {
            'request': {
                'query': 'test',
                'max_results': 5,
                'published_after': '2024-01-01'
            }
        }
    }


@pytest.fixture
def mock_youtube_config():
    """Mock YouTube configuration for testing."""
    config = Mock(spec=YouTubeConfig)
    config.api_key = "test_api_key_123"
    config.max_results = 10
    config.default_language = "en"
    return config


@pytest.fixture
def sample_youtube_api_response():
    """Sample YouTube API search response."""
    return {
        "kind": "youtube#searchListResponse",
        "items": [
            {
                "kind": "youtube#searchResult",
                "id": {
                    "kind": "youtube#video",
                    "videoId": "dQw4w9WgXcQ"  # 11 characters, valid YouTube ID pattern
                },
                "snippet": {
                    "title": "Test Video 1",
                    "description": "This is a test video description 1",
                    "channelTitle": "Test Channel 1",
                    "publishedAt": "2024-01-01T12:00:00Z",
                    "thumbnails": {
                        "default": {"url": "https://example.com/thumb1.jpg"}
                    },
                },
            },
            {
                "kind": "youtube#searchResult",
                "id": {
                    "kind": "youtube#video",
                    "videoId": "ScMzIvxBSi4"  # 11 characters, valid YouTube ID pattern
                },
                "snippet": {
                    "title": "Test Video 2",
                    "description": "This is a test video description 2",
                    "channelTitle": "Test Channel 2",
                    "publishedAt": "2024-01-02T12:00:00Z",
                    "thumbnails": {
                        "default": {"url": "https://example.com/thumb2.jpg"}
                    },
                },
            },
        ],
    }


@pytest.fixture
def sample_transcript_response():
    """Sample transcript response from YouTube Transcript API."""
    return [
        {
            "text": "Hello everyone, welcome to this video.",
            "start": 0.0,
            "duration": 3.0,
        },
        {"text": "Today we'll be discussing testing.", "start": 3.0, "duration": 2.5},
        {"text": "Let's get started with the basics.", "start": 5.5, "duration": 2.0},
    ]


@pytest.fixture
def sample_youtube_video():
    """Sample YouTubeVideo instance for testing."""
    return YouTubeVideo(
        video_id="dQw4w9WgXcQ",  # 11 characters, valid YouTube ID
        title="Test Video Title",
        description="Test video description",
        channel="Test Channel",
        published_at="2024-01-01T12:00:00Z",
        thumbnail="https://example.com/thumb.jpg",
        transcript="This is a test transcript content.",
    )


@pytest.fixture
def sample_youtube_video_1():
    """First sample YouTubeVideo for multi-video tests."""
    return YouTubeVideo(
        video_id="dQw4w9WgXcQ",  # 11 characters
        title="Video 1",
        description="Desc 1",
        channel="Channel 1",
        published_at="2024-01-01T12:00:00Z",
        thumbnail="thumb1.jpg",
        transcript="Transcript 1"
    )


@pytest.fixture
def sample_youtube_video_2():
    """Second sample YouTubeVideo for multi-video tests."""
    return YouTubeVideo(
        video_id="ScMzIvxBSi4",  # 11 characters
        title="Video 2",
        description="Desc 2",
        channel="Channel 2",
        published_at="2024-01-02T12:00:00Z",
        thumbnail="thumb2.jpg",
        transcript="Transcript 2"
    )


@pytest.fixture
def sample_youtube_video_for_json_test():
    """YouTubeVideo for JSON format testing."""
    return YouTubeVideo(
        video_id="jNQXAC9IVRw",  # 11 characters
        title="Test Video",
        description="Test Description",
        channel="Test Channel",
        published_at="2024-01-01T12:00:00Z",
        thumbnail="https://example.com/thumb.jpg",
        transcript="Test transcript"
    )


@pytest.fixture
def mock_youtube_searcher():
    """Mock YouTube searcher with empty results by default."""
    mock_searcher = AsyncMock()
    mock_searcher.search_videos.return_value = []
    return mock_searcher


@pytest.fixture
def mock_youtube_searcher_sync(mock_youtube_config):
    """Mock synchronous YouTubeSearcher instance for testing."""
    from unittest.mock import patch, Mock
    from mcp_server_youtube.youtube.module import YouTubeSearcher
    
    with patch('mcp_server_youtube.youtube.module.build') as mock_build:
        mock_service = Mock()
        mock_build.return_value = mock_service
        
        searcher = YouTubeSearcher(mock_youtube_config)
        return searcher


@pytest.fixture
def mock_context(mock_youtube_searcher):
    """Mock context with youtube_searcher for testing."""
    context = Mock()
    context.lifespan_context = {"youtube_searcher": mock_youtube_searcher}
    return context
