import pytest
from unittest.mock import Mock

from mcp_server_youtube.youtube.config import YouTubeConfig
from mcp_server_youtube.youtube.models import YouTubeVideo


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
                    "videoId": "test_video_id_1"
                },
                "snippet": {
                    "title": "Test Video 1",
                    "description": "This is a test video description 1",
                    "channelTitle": "Test Channel 1",
                    "publishedAt": "2024-01-01T12:00:00Z",
                    "thumbnails": {
                        "default": {
                            "url": "https://example.com/thumb1.jpg"
                        }
                    }
                }
            },
            {
                "kind": "youtube#searchResult",
                "id": {
                    "kind": "youtube#video",
                    "videoId": "test_video_id_2"
                },
                "snippet": {
                    "title": "Test Video 2",
                    "description": "This is a test video description 2",
                    "channelTitle": "Test Channel 2",
                    "publishedAt": "2024-01-02T12:00:00Z",
                    "thumbnails": {
                        "default": {
                            "url": "https://example.com/thumb2.jpg"
                        }
                    }
                }
            }
        ]
    }


@pytest.fixture
def sample_transcript_response():
    """Sample transcript response from YouTube Transcript API."""
    return [
        {"text": "Hello everyone, welcome to this video.", "start": 0.0, "duration": 3.0},
        {"text": "Today we'll be discussing testing.", "start": 3.0, "duration": 2.5},
        {"text": "Let's get started with the basics.", "start": 5.5, "duration": 2.0}
    ]


@pytest.fixture
def sample_youtube_video():
    """Sample YouTubeVideo instance for testing."""
    return YouTubeVideo(
        video_id="test_video_id",
        title="Test Video Title",
        description="Test video description",
        channel="Test Channel",
        published_at="2024-01-01T12:00:00Z",
        thumbnail="https://example.com/thumb.jpg",
        transcript="This is a test transcript content."
    )
