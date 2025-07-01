import logging
import base64
import io
import ssl
import asyncio
from functools import lru_cache
from typing import Optional
import aiohttp
import tweepy
import requests
import anyio
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, before_sleep_log, retry_if_exception
from tweepy import API, Client, OAuth1UserHandler
from tweepy.asynchronous import AsyncClient
from tweepy.errors import TweepyException, HTTPException
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


def is_retryable_tweepy_error(exception: Exception) -> bool:
    """Return True if the exception is a TweepyException with a 5xx status code."""
    if not isinstance(exception, TweepyException):
        return False

    response = getattr(exception, "response", None)
    if response is None:
        return False

    return 500 <= response.status_code < 600


retry_async_wrapper = retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(min=0.5, max=10),
    retry=retry_if_exception_type(aiohttp.ClientError) | retry_if_exception(is_retryable_tweepy_error),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)

retry_sync_in_async_wrapper = retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(min=0.5, max=10),
    retry=retry_if_exception_type(requests.exceptions.RequestException) | retry_if_exception(is_retryable_tweepy_error),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)


class AsyncTwitterClient:
    def __init__(self, config):
        """
        Initialize Twitter API client with provided configuration.
        """
        self.config = config

        # Create a custom SSL context
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = True
        self.ssl_context.verify_mode = ssl.CERT_REQUIRED

        self.client = AsyncClient(
            consumer_key=config.API_KEY,
            consumer_secret=config.API_SECRET_KEY,
            access_token=config.ACCESS_TOKEN,
            access_token_secret=config.ACCESS_TOKEN_SECRET,
            bearer_token=config.BEARER_TOKEN,
            wait_on_rate_limit=True
        )

        auth = OAuth1UserHandler(config.API_KEY, config.API_SECRET_KEY)
        auth.set_access_token(config.ACCESS_TOKEN, config.ACCESS_TOKEN_SECRET)
        self._sync_api = API(auth, wait_on_rate_limit=True)

    @retry_sync_in_async_wrapper
    async def _upload_media(self, image_content_str: str):
        """
        Internal method to upload media to Twitter.
        Note: Using sync client as Tweepy doesn't support async media upload yet.
        """
        image_content = base64.b64decode(image_content_str)
        image_file = io.BytesIO(image_content)
        image_file.name = "image.png"
        
        media = await anyio.to_thread.run_sync(
            lambda: self._sync_api.media_upload(filename=image_file.name, file=image_file)
        )
        return media

    @retry_async_wrapper
    async def create_tweet(
            self,
            text: str,
            image_content_str: str | None = None,
            poll_options: list[str] | None = None,
            poll_duration: int | None = None,
            in_reply_to_tweet_id: str | None = None,
            quote_tweet_id: str | None = None
    ):
        """
        Create a new tweet with optional media, polls, replies or quotes.

        Args:
            text (str): The text content of the tweet. Will be truncated to the
                configured maximum tweet length if necessary.
            image_content_str (str, optional): A Base64-encoded string of image data
                to attach as media. Requires media uploads to be enabled in config.
            poll_options (list[str], optional): A list of 2 to N options (where N is
                config.poll_max_options) to include in a poll.
            poll_duration (int, optional): Duration of the poll in minutes (must be
                between 5 and config.poll_max_duration).
            in_reply_to_tweet_id (str, optional): The ID of an existing tweet to reply to.
                Note: Your `text` must include "@username" of the tweet's author.
            quote_tweet_id (str, optional): The ID of an existing tweet to quote. The
                quoted tweet will appear inline, with your `text` shown above it.

        Returns:
            tweepy.Response: The response from Twitter API containing the created tweet data.

        Raises:
            ValueError: If poll_options length is out of bounds or poll_duration is invalid.
            Exception: Propagates any error from the Twitter API client or media upload.
        """
        try:
            media_ids = []
            if image_content_str and self.config.media_upload_enabled:
                media = await self._upload_media(image_content_str)
                media_ids.append(media.media_id)

            poll_params = {}
            if poll_options:
                if len(poll_options) < 2 or len(poll_options) > self.config.poll_max_options:
                    raise ValueError(f"Poll must have 2-{self.config.poll_max_options} options")
                if not poll_duration or not 5 <= poll_duration <= self.config.poll_max_duration:
                    raise ValueError(f"Poll duration must be 5-{self.config.poll_max_duration} minutes")

                poll_params = {
                    "poll_options": poll_options,
                    "poll_duration_minutes": poll_duration
                }
            response = await self.client.create_tweet(
                text=text[:self.config.max_tweet_length],
                media_ids=media_ids or None,
                in_reply_to_tweet_id=in_reply_to_tweet_id,
                quote_tweet_id=quote_tweet_id,
                **poll_params)
            return response.data["id"]

        except Exception as e:
            logger.error(f"Failed to create tweet: {e}", exc_info=True)
            raise

    @retry_async_wrapper
    async def retweet_tweet(self, tweet_id: str):
        """
        Retweet an existing tweet asynchronously.

        Args:
            tweet_id (str): The ID of the tweet to retweet

        Returns:
            str: Success message
        """
        try:
            await self.client.retweet(tweet_id=tweet_id)
            return f"Successfully retweet post {tweet_id}"
        except Exception as e:
            logger.error(f"Failed to retweet tweet {tweet_id}: {e}", exc_info=True)
            raise

    @retry_async_wrapper
    async def get_user_tweets(self, user_id: str, max_results: int = 10):
        """
        Retrieve recent tweets posted by a specified user asynchronously.

        Args:
            user_id (str): The ID of the user
            max_results (int, optional): Maximum number of tweets to return

        Returns:
            tweepy.Response: Response object with tweet data, or raises exception on error
        """
        try:
            tweets = await self.client.get_users_tweets(
                id=user_id,
                max_results=max_results,
                tweet_fields=["id", "text", "created_at"]
            )
            return tweets
        except Exception as e:
            logger.error(f"Error getting user tweets for user_id {user_id}: {str(e)}")
            if "401" in str(e) or "Unauthorized" in str(e):
                logger.error("Twitter API 401 Unauthorized - This usually means:")
                logger.error("1. Your Twitter app doesn't have 'Read' permissions")
                logger.error("2. Your app needs Twitter API v2 'tweet.read' scope")
                logger.error("3. You may need to regenerate your access tokens after changing permissions")
                logger.error("4. For reading other users' tweets, you may need elevated access")
            raise

    @retry_async_wrapper
    async def follow_user(self, user_id: str):
        """
        Follow another Twitter user asynchronously.

        Args:
            user_id (str): The ID of the user to follow

        Returns:
            str: Success message
        """
        try:
            await self.client.follow_user(user_id=user_id)
            return f"Successfully followed user: {user_id}"
        except Exception as e:
            logger.error(f"Failed to follow user {user_id}: {e}", exc_info=True)
            raise

    @retry_async_wrapper
    async def initialize(self):
        """
        Initialize and test the Twitter client connection.
        """
        try:
            user = await self.client.get_me()
            logger.info(f"Successfully authenticated as: {user.data['username']}")
            return self
        except Exception as e:
            logger.error(f"Failed to authenticate: {str(e)}")
            raise


_twitter_client: AsyncTwitterClient | None = None
_client_lock = asyncio.Lock()

async def get_twitter_client() -> AsyncTwitterClient:
    global _twitter_client
    if _twitter_client is not None:
        return _twitter_client
    async with _client_lock:
        if _twitter_client is None:
            logger.info("Creating AsyncTwitterClient instance…")
            from .config import TwitterConfig
            config = TwitterConfig()
            client = AsyncTwitterClient(config=config)
            _twitter_client = await client.initialize()
        return _twitter_client