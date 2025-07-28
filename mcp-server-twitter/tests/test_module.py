from unittest.mock import AsyncMock, MagicMock

from aioresponses import aioresponses
import logging
import aiohttp
import pytest
from mcp_server_twitter.twitter.module import AsyncTwitterClient
from tweepy.errors import TweepyException
import requests


@pytest.fixture
def mock_config():
    """Provides a mock config object for the Twitter client."""
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


@pytest.mark.asyncio
async def test_create_tweet_retries_on_aiohttp_client_error(
    mock_config, mocker, caplog
):
    """
    Test that create_tweet retries on aiohttp.ClientError and eventually succeeds.
    """
    # Arrange
    twitter_client = AsyncTwitterClient(config=mock_config)

    # Mock the internal tweepy AsyncClient
    mock_async_client = AsyncMock()

    # Simulate failure twice, then success
    mock_async_client.create_tweet.side_effect = [
        aiohttp.ClientError("First failure"),
        aiohttp.ClientError("Second failure"),
        MagicMock(data={"id": "12345"}),  # Successful response
    ]

    # Patch the client instance used by our class
    mocker.patch.object(twitter_client, "client", mock_async_client)

    # Act
    import logging

    caplog.set_level(logging.WARNING)
    tweet_id = await twitter_client.create_tweet(text="Hello world")

    # Assert
    assert tweet_id == "12345"
    assert mock_async_client.create_tweet.call_count == 3

    # We expect 2 WARNING logs from tenacity for the retries
    retry_logs = [rec for rec in caplog.records if rec.levelno == logging.WARNING]
    assert len(retry_logs) == 2
    assert "Retrying" in caplog.text
    assert "ClientError: Second failure" in caplog.text


@pytest.mark.asyncio
async def test_create_tweet_fails_after_max_retries(mock_config, mocker):
    """
    Test that create_tweet fails after the maximum number of retries.
    """
    # Arrange
    twitter_client = AsyncTwitterClient(config=mock_config)

    mock_async_client = AsyncMock()

    # Simulate persistent failure
    mock_async_client.create_tweet.side_effect = aiohttp.ClientError(
        "Persistent failure"
    )

    mocker.patch.object(twitter_client, "client", mock_async_client)

    # Act & Assert
    with pytest.raises(aiohttp.ClientError):
        await twitter_client.create_tweet(text="This will fail")

    assert mock_async_client.create_tweet.call_count == 5


@pytest.mark.asyncio
async def test_create_tweet_retries_on_tweepy_5xx_error(mock_config, mocker):
    """
    Test that create_tweet retries on a TweepyException with a 5xx status code.
    """
    # Arrange
    twitter_client = AsyncTwitterClient(config=mock_config)
    mock_async_client = AsyncMock()

    # Mock a 503 Service Unavailable error
    mock_response = MagicMock()
    mock_response.status_code = 503
    tweepy_exception = TweepyException("Service Unavailable")
    tweepy_exception.response = mock_response

    mock_async_client.create_tweet.side_effect = [
        tweepy_exception,
        MagicMock(data={"id": "54321"}),
    ]

    mocker.patch.object(twitter_client, "client", mock_async_client)

    # Act
    tweet_id = await twitter_client.create_tweet(text="Testing 5xx retry")

    # Assert
    assert tweet_id == "54321"
    assert mock_async_client.create_tweet.call_count == 2


@pytest.mark.asyncio
async def test_retweet_retries_and_succeeds(mock_config, mocker, caplog):
    """
    Test that retweet_tweet retries on failure and eventually succeeds.
    """
    # Arrange
    twitter_client = AsyncTwitterClient(config=mock_config)
    mock_async_client = AsyncMock()

    mock_async_client.retweet.side_effect = [
        aiohttp.ClientError("Retweet failed"),
        AsyncMock(),  # Success
    ]
    mocker.patch.object(twitter_client, "client", mock_async_client)

    import logging

    caplog.set_level(logging.WARNING)

    # Act
    result = await twitter_client.retweet_tweet(tweet_id="123")

    # Assert
    assert result == "Successfully retweet post 123"
    assert mock_async_client.retweet.call_count == 2
    assert "Retrying" in caplog.text
    assert "raised ClientError: Retweet failed" in caplog.text


@pytest.mark.asyncio
async def test_create_tweet_success_with_media(mock_config, mocker):
    """Test creating a tweet with an image successfully."""
    # Arrange
    twitter_client = AsyncTwitterClient(config=mock_config)
    mock_async_client = AsyncMock()
    mock_async_client.create_tweet.return_value = MagicMock(data={"id": "124"})

    # Mock the internal upload method to avoid testing it here
    mocker.patch.object(
        twitter_client, "_upload_media", new_callable=AsyncMock
    ).return_value = MagicMock(media_id="media123")
    mocker.patch.object(twitter_client, "client", mock_async_client)

    # A valid 1x1 png base64 string
    image_str = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="

    # Act
    tweet_id = await twitter_client.create_tweet(
        text="A tweet with an image", image_content_str=image_str
    )

    # Assert
    assert tweet_id == "124"
    twitter_client._upload_media.assert_awaited_once_with(image_str)
    mock_async_client.create_tweet.assert_awaited_once_with(
        text="A tweet with an image",
        media_ids=["media123"],
        in_reply_to_tweet_id=None,
        quote_tweet_id=None,
    )


@pytest.mark.asyncio
async def test_create_tweet_success_with_poll(mock_config, mocker):
    """Test creating a tweet with a poll successfully."""
    # Arrange
    twitter_client = AsyncTwitterClient(config=mock_config)
    mock_async_client = AsyncMock()
    mock_async_client.create_tweet.return_value = MagicMock(data={"id": "125"})
    mocker.patch.object(twitter_client, "client", mock_async_client)

    # Act
    tweet_id = await twitter_client.create_tweet(
        text="A poll", poll_options=["Yes", "No"], poll_duration=60
    )

    # Assert
    assert tweet_id == "125"
    mock_async_client.create_tweet.assert_awaited_once_with(
        text="A poll",
        media_ids=None,
        in_reply_to_tweet_id=None,
        quote_tweet_id=None,
        poll_options=["Yes", "No"],
        poll_duration_minutes=60,
    )


@pytest.mark.asyncio
async def test_create_tweet_fails_on_invalid_poll(mock_config):
    """Test that creating a tweet with invalid poll options raises ValueError immediately."""
    # Arrange
    twitter_client = AsyncTwitterClient(config=mock_config)

    # Act & Assert
    with pytest.raises(ValueError, match="Poll must have 2-4 options"):
        await twitter_client.create_tweet(text="Poll", poll_options=["Only one"])

    with pytest.raises(ValueError, match="Poll duration must be 5-10080 minutes"):
        await twitter_client.create_tweet(
            text="Poll", poll_options=["Yes", "No"], poll_duration=4
        )


# --- Tests for _upload_media (Sync Retry Logic) ---


@pytest.mark.asyncio
async def test_upload_media_retries_on_requests_exception(mock_config, mocker, caplog):
    """Test that the sync media upload retries on requests.RequestException."""
    # Arrange
    caplog.set_level(logging.WARNING)
    twitter_client = AsyncTwitterClient(config=mock_config)
    mock_media_obj = MagicMock(media_id="media123")
    mock_run_sync = mocker.patch("anyio.to_thread.run_sync", new_callable=AsyncMock)
    mock_run_sync.side_effect = [
        requests.exceptions.RequestException("Sync connection error"),
        mock_media_obj,
    ]

    # Act
    result = await twitter_client._upload_media(image_content_str="base64string")

    # Assert
    assert result.media_id == "media123"
    assert mock_run_sync.call_count == 2
    assert "Retrying" in caplog.text


# --- Tests for get_user_tweets ---


@pytest.mark.asyncio
async def test_get_user_tweets_401_error_logs_details(mock_config, mocker, caplog):
    """Test that a 401 Unauthorized error logs specific helpful messages."""
    # Arrange
    caplog.set_level(logging.ERROR)
    twitter_client = AsyncTwitterClient(config=mock_config)
    mock_async_client = AsyncMock()
    mock_async_client.get_users_tweets.side_effect = Exception("401 Unauthorized")
    mocker.patch.object(twitter_client, "client", mock_async_client)

    # Act & Assert
    with pytest.raises(Exception, match="401 Unauthorized"):
        await twitter_client.get_user_tweets(user_id="user1")

    assert "Twitter API 401 Unauthorized" in caplog.text
    assert "Your app needs Twitter API v2 'tweet.read' scope" in caplog.text


# --- Tests for search_hashtag ---


@pytest.mark.asyncio
async def test_search_hashtag_success_and_adds_hash(mock_config, mocker):
    """Test a successful hashtag search and that '#' is added if missing."""
    # Arrange
    twitter_client = AsyncTwitterClient(config=mock_config)
    mock_async_client = AsyncMock()
    mock_tweet = MagicMock(text="A tweet about python")
    mock_async_client.search_recent_tweets.return_value = MagicMock(data=[mock_tweet])
    mocker.patch.object(twitter_client, "client", mock_async_client)

    # Act
    results = await twitter_client.search_hashtag(hashtag="python")

    # Assert
    assert results == ["A tweet about python"]
    call_args = mock_async_client.search_recent_tweets.call_args
    assert call_args.kwargs["query"] == "#python"


# NOTE: You will need to import 'aioresponses' at the top of your test file.


@pytest.mark.asyncio
async def test_get_trends_success(mock_config, mocker):
    """Test successfully fetching trends using aioresponses."""
    # Arrange
    twitter_client = AsyncTwitterClient(config=mock_config)
    egypt_woeid = 23424802

    url = f"https://api.twitter.com/2/trends/by/woeid/{egypt_woeid}?max_trends=50"

    mock_payload = {"data": [{"trend_name": "#Cairo"}, {"trend_name": "#Egypt"}]}

    with aioresponses() as m:
        m.get(url, status=200, payload=mock_payload)

        # Act
        trends = await twitter_client.get_trends(
            countries=["Egypt"]
        )  # This uses max_trends=50 by default

        # Assert
        assert trends["Egypt"] == ["#Cairo", "#Egypt"]


@pytest.mark.asyncio
async def test_get_trends_handles_api_error(mock_config, mocker):
    """Test handling of an API error using aioresponses."""
    # Arrange
    twitter_client = AsyncTwitterClient(config=mock_config)
    egypt_woeid = 23424802

    url = f"https://api.twitter.com/2/trends/by/woeid/{egypt_woeid}?max_trends=50"

    with aioresponses() as m:
        m.get(url, status=401, payload={"error": "Unauthorized"})

        # Act
        trends = await twitter_client.get_trends(countries=["Egypt"])

        # Assert
        assert "Error: 401" in trends["Egypt"][0]
        assert "Unauthorized" in trends["Egypt"][0]
