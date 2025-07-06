from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest
from mcp_server_twitter.twitter.module import AsyncTwitterClient
from tweepy.errors import TweepyException


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
