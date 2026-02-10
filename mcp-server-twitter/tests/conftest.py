"""
Shared test fixtures for mcp-server-twitter tests.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastmcp import Context

from mcp_server_twitter.schemas import (
    CreateTweetRequest,
    FollowUserRequest,
    GetTrendsRequest,
    GetUserTweetsRequest,
    RetweetTweetRequest,
    SearchHashtagRequest,
)


class MockTwitterResponse:
    """Mock class for Twitter API responses."""

    def __init__(self, data=None):
        self.data = data


class MockTweet:
    """Mock class for individual tweet objects."""

    def __init__(self, text):
        self.text = text
        self.id = "mock_id_123"  # Added a default ID for consistent behavior


@pytest.fixture
def mock_context():
    """
    Create a mock Context object with twitter_client.

    This fixture provides a properly configured mock Context that can be used
    across all server tests requiring a Context instance with twitter_client.
    """
    ctx = MagicMock(spec=Context)
    ctx.request_context.lifespan_context = {"twitter_client": AsyncMock()}
    return ctx


@pytest.fixture
def mock_twitter_response():
    """
    Provides a mock for Twitter API responses, returning directly serializable data.
    """

    def _mock_response(data=None, errors=None):
        response = {"data": data} if data is not None else {}
        if errors is not None:
            response["errors"] = errors
        return response

    return _mock_response


@pytest.fixture
def mock_tweet():
    """Mock class for individual tweet objects as a dictionary."""

    def _mock_tweet(text, id="mock_id_123"):
        return {"text": text, "id": id}

    return _mock_tweet


@pytest.fixture
def mcp_server_tools():
    """
    Provides access to MCP server tools for testing.

    Returns a dictionary with all available tool functions.
    """
    from mcp_server_twitter.server import mcp_server

    return {
        "create_tweet": mcp_server._tool_manager._tools["create_tweet"].fn,
        "get_user_tweets": mcp_server._tool_manager._tools["get_user_tweets"].fn,
        "follow_user": mcp_server._tool_manager._tools["follow_user"].fn,
        "retweet_tweet": mcp_server._tool_manager._tools["retweet_tweet"].fn,
        "get_trends": mcp_server._tool_manager._tools["get_trends"].fn,
        "search_hashtag": mcp_server._tool_manager._tools["search_hashtag"].fn,
    }


@pytest.fixture
def sample_tool_inputs():
    """
    Provides sample tool input data for testing.

    Returns a dictionary with valid tool inputs for each tool function.
    """
    return {
        "create_tweet": {
            "simple": {"text": "Hello world"},
            "with_poll": {
                "text": "What's your favorite language?",
                "poll_options": ["Python", "JavaScript", "Go"],
                "poll_duration": 60,
            },
            "with_image": {
                "text": "Check out this image",
                "image_content_str": "base64encodedimagedata==",
            },
        },
        "get_user_tweets": {
            "single_user": {"user_ids": ["user123"]},
            "multiple_users": {
                "user_ids": ["user1", "user2", "user3"],
                "max_results": 5,
            },
        },
        "follow_user": {"user_id": "target_user"},
        "retweet_tweet": {"tweet_id": "12345"},
        "get_trends": {
            "single_country": {"countries": ["USA"]},
            "multiple_countries": {
                "countries": ["USA", "Egypt", "France"],
                "max_trends": 10,
            },
        },
        "search_hashtag": {
            "simple": {"hashtag": "#python"},
            "with_max_results": {"hashtag": "#ai", "max_results": 50},
        },
    }


@pytest.fixture
def mock_config():
    """
    Provides a mock TwitterConfig object for testing.

    This fixture creates a properly configured mock that can be used
    across all tests requiring a TwitterConfig instance.
    """
    config = MagicMock()
    config.API_KEY = "test_api_key"
    config.API_SECRET_KEY = "test_api_secret_key"
    config.ACCESS_TOKEN = "test_access_token"
    config.ACCESS_TOKEN_SECRET = "test_access_token_secret"
    config.BEARER_TOKEN = "test_bearer_token"
    config.media_upload_enabled = True
    config.max_tweet_length = 280
    config.poll_max_options = 4
    config.poll_max_duration = 10080  # 7 days in minutes
    return config


@pytest.fixture
def sample_base64_image():
    """
    Provides a valid 1x1 PNG image encoded in base64.

    This is useful for testing media upload functionality without
    needing actual image files.
    """
    return "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="


@pytest.fixture
def sample_tweet_data():
    """
    Provides sample tweet data structures for testing.

    Returns a dictionary with various tweet-related test data.
    """
    return {
        "tweet_id": "12345",
        "user_id": "user123",
        "tweet_text": "This is a test tweet",
        "hashtag": "python",
        "poll_options": ["Yes", "No", "Maybe"],
        "poll_duration": 60,
        "countries": ["Egypt", "France", "United States"],
    }


@pytest.fixture
def mock_tweet_response():
    """
    Provides a mock tweet response object.

    Simulates the structure returned by Twitter API for tweet operations.
    """
    response = MagicMock()
    response.data = {"id": "12345"}
    return response


@pytest.fixture
def mock_trends_response():
    """
    Provides a mock trends response for testing get_trends functionality.
    """
    # Return directly a dictionary that is JSON serializable
    return {"Egypt": ["#TestTrend1", "#TestTrend2"], "USA": ["#TestTrend3"]}


@pytest.fixture
def mock_user_tweets_response():
    """
    Provides a mock user tweets response as a serializable list of dictionaries.
    """

    def _mock_user_tweets(tweets_data):
        # Expects a list of dictionaries like [{"text": "Tweet 1", "id": "1"}]
        # or a list of strings if only text is needed.
        # For compatibility with existing tests, if tweets_data are simple strings, convert them
        if tweets_data and isinstance(tweets_data[0], str):
            return [{"text": t, "id": f"id_{i}"} for i, t in enumerate(tweets_data)]
        return tweets_data

    return _mock_user_tweets


@pytest.fixture
def mock_media_upload():
    """
    Provides a mock media upload response.
    """
    media = MagicMock()
    media.media_id = "media123"
    return media


@pytest.fixture
def mock_tweepy_exception_5xx():
    """
    Provides a mock TweepyException with 5xx status code.
    """
    mock_response = MagicMock()
    mock_response.status_code = 503
    exception = MagicMock()
    exception.response = mock_response
    return exception


# === Schema Testing Fixtures ===


@pytest.fixture
def schema_constants():
    """
    Provides commonly used constants for schema validation testing.

    Returns a dictionary with boundary values and limits used across schemas.
    """
    return {
        # Text length limits
        "min_text_length": 1,
        "max_text_length": 280,
        "over_max_text_length": 281,
        # Poll constraints
        "min_poll_options": 2,
        "max_poll_options": 4,
        "over_max_poll_options": 5,
        "min_poll_duration": 5,
        "max_poll_duration": 10080,  # 1 week in minutes
        "under_min_poll_duration": 4,
        "over_max_poll_duration": 10081,
        # Results limits for different schemas
        "user_tweets_min_results": 1,
        "user_tweets_max_results": 100,
        "user_tweets_over_max": 999,
        "user_tweets_default": 10,
        "trends_min_results": 1,
        "trends_max_results": 50,
        "trends_over_max": 999,
        "trends_default": 50,
        "hashtag_min_results": 10,
        "hashtag_max_results": 100,
        "hashtag_under_min": 5,
        "hashtag_over_max": 200,
        "hashtag_default": 10,
    }


@pytest.fixture
def common_test_data():
    """
    Provides commonly used test data across schema tests.

    Returns a dictionary with frequently used strings, IDs, and lists.
    """
    return {
        # Common texts
        "simple_text": "Hello world!",
        "minimal_text": "Hello",
        "reply_text": "This is a reply",
        "quote_text": "Quoting this",
        "poll_question": "Poll question?",
        "image_text": "Check this image!",
        "unicode_text": "Hello 🌍! This is a test with émojis and spécial chars ñ",
        # Common IDs
        "user_id": "user123",
        "tweet_id": "123456789",
        "reply_tweet_id": "123456789",
        "quote_tweet_id": "987654321",
        "numeric_user_id": "123456789",
        "alphanumeric_user_id": "user_123_abc",
        "alphanumeric_tweet_id": "tweet_123_abc",
        # Common lists
        "poll_options_min": ["A", "B"],
        "poll_options_max": ["A", "B", "C", "D"],
        "poll_options_yes_no": ["Yes", "No"],
        "poll_options_long": ["Option A", "Option B"],
        "poll_options_special": ["Option #1", "Choice & More", "2nd Option", "Final!"],
        "poll_options_too_few": ["a"],
        "poll_options_too_many": ["A", "B", "C", "D", "E"],
        "single_user_list": ["user123"],
        "multiple_users": ["user1", "user2", "user3"],
        "empty_list": [],
        "single_country": ["USA"],
        "multiple_countries": ["USA", "Canada", "UK", "France", "Germany"],
        # Common values
        "base64_image": "base64encodedcontent",
        "standard_duration": 60,
        "hashtag_with_hash": "#python",
        "hashtag_without_hash": "python",
        "hashtag_with_underscore": "#machine_learning",
    }


@pytest.fixture
def schema_factories():
    """
    Provides factory functions for creating schema instances with default valid data.

    Each factory function accepts optional parameters to override defaults.
    """
    # Removed explicit imports as they are already at the top
    # from mcp_server_twitter.schemas import (
    #     CreateTweetInput,
    #     GetUserTweetsInput,
    #     FollowUserInput,
    #     RetweetTweetInput,
    #     GetTrendsInput,
    #     SearchHashtagInput,
    # )

    def create_tweet_factory(
        text="Test tweet",
        image_content_str=None,
        poll_options=None,
        poll_duration=None,
        in_reply_to_tweet_id=None,
        quote_tweet_id=None,
    ):
        return CreateTweetRequest(
            text=text,
            image_content_str=image_content_str,
            poll_options=poll_options,
            poll_duration=poll_duration,
            in_reply_to_tweet_id=in_reply_to_tweet_id,
            quote_tweet_id=quote_tweet_id,
        )

    def get_user_tweets_factory(user_ids=None, max_results=None):
        if user_ids is None:
            user_ids = ["test_user"]
        return GetUserTweetsRequest(user_ids=user_ids, max_results=max_results)

    def follow_user_factory(user_id="test_user"):
        return FollowUserRequest(user_id=user_id)

    def retweet_factory(tweet_id="test_tweet_123"):
        return RetweetTweetRequest(tweet_id=tweet_id)

    def get_trends_factory(countries=None, max_trends=None):
        if countries is None:
            countries = ["USA"]
        return GetTrendsRequest(countries=countries, max_trends=max_trends)

    def search_hashtag_factory(hashtag="#test", max_results=None):
        return SearchHashtagRequest(hashtag=hashtag, max_results=max_results)

    return {
        "create_tweet": create_tweet_factory,
        "get_user_tweets": get_user_tweets_factory,
        "follow_user": follow_user_factory,
        "retweet": retweet_factory,
        "get_trends": get_trends_factory,
        "search_hashtag": search_hashtag_factory,
    }


@pytest.fixture
def boundary_test_data(schema_constants, common_test_data):
    """
    Provides test data specifically for boundary value testing.

    Combines schema_constants and common_test_data to create boundary test scenarios.
    """
    return {
        # Text boundaries
        "max_length_text": "a" * schema_constants["max_text_length"],
        "over_max_text": "a" * schema_constants["over_max_text_length"],
        "empty_text": "",
        # Poll boundaries
        "min_poll_data": {
            "options": common_test_data["poll_options_min"],
            "duration": schema_constants["min_poll_duration"],
        },
        "max_poll_data": {
            "options": common_test_data["poll_options_max"],
            "duration": schema_constants["max_poll_duration"],
        },
        # Results boundaries
        "user_tweets_boundaries": {
            "min": schema_constants["user_tweets_min_results"],
            "max": schema_constants["user_tweets_max_results"],
            "over_max": schema_constants["user_tweets_over_max"],
            "zero": 0,
            "negative": -5,
        },
        "trends_boundaries": {
            "min": schema_constants["trends_min_results"],
            "max": schema_constants["trends_max_results"],
            "over_max": schema_constants["trends_over_max"],
            "zero": 0,
            "negative": -5,
        },
        "hashtag_boundaries": {
            "min": schema_constants["hashtag_min_results"],
            "max": schema_constants["hashtag_max_results"],
            "under_min": schema_constants["hashtag_under_min"],
            "over_max": schema_constants["hashtag_over_max"],
            "zero": 0,
            "negative": -1,
        },
    }
