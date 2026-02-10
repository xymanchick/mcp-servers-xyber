import asyncio
import base64
import io
import os
import ssl

import aiohttp
import anyio
import requests
from tenacity import (
    retry,
    retry_if_exception,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)
from tweepy import API, OAuth1UserHandler
from tweepy.asynchronous import AsyncClient
from tweepy.errors import TweepyException

from mcp_server_twitter.errors import (
    TwitterAPIError,
    TwitterAuthenticationError,
    TwitterClientError,
    TwitterMediaUploadError,
    map_aiohttp_error,
    map_tweepy_error,
    on_final_retry_failure,
)
from mcp_server_twitter.logging_config import get_logger, log_retry_attempt
from mcp_server_twitter.metrics import async_operation_timer, async_timed

logger = get_logger(__name__)


def is_retryable_tweepy_error(exception: Exception) -> bool:
    """Return True if the exception is a TweepyException with a 5xx status code."""
    if not isinstance(exception, TweepyException):
        return False

    response = getattr(exception, "response", None)
    if response is None:
        return False

    is_retryable = 500 <= response.status_code < 600

    logger.debug(
        "Checking if Tweepy error is retryable",
        extra={
            "error_type": type(exception).__name__,
            "status_code": response.status_code,
            "is_retryable": is_retryable,
        },
    )

    return is_retryable


# Enhanced retry wrappers with proper final failure handling
retry_async_wrapper = retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(min=0.5, max=10),
    retry=retry_if_exception_type(aiohttp.ClientError)
    | retry_if_exception(is_retryable_tweepy_error),
    before_sleep=log_retry_attempt,
    retry_error_callback=on_final_retry_failure,
    reraise=True,
)

retry_sync_in_async_wrapper = retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(min=0.5, max=10),
    retry=retry_if_exception_type(requests.exceptions.RequestException)
    | retry_if_exception(is_retryable_tweepy_error),
    before_sleep=log_retry_attempt,
    retry_error_callback=on_final_retry_failure,
    reraise=True,
)


class AsyncTwitterClient:
    def __init__(self, config):
        """Initialize Twitter API client with enhanced logging."""
        self.config = config

        logger.info(
            "Initializing AsyncTwitterClient",
            extra={
                "media_upload_enabled": config.media_upload_enabled,
                "max_tweet_length": config.max_tweet_length,
                "poll_max_options": config.poll_max_options,
                "poll_max_duration": config.poll_max_duration,
            },
        )

        # Create a custom SSL context
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = True
        self.ssl_context.verify_mode = ssl.CERT_REQUIRED

        try:
            self.client = AsyncClient(
                consumer_key=config.API_KEY,
                consumer_secret=config.API_SECRET_KEY,
                access_token=config.ACCESS_TOKEN,
                access_token_secret=config.ACCESS_TOKEN_SECRET,
                bearer_token=config.BEARER_TOKEN,
                wait_on_rate_limit=True,
            )

            logger.debug("AsyncClient created successfully")

            auth = OAuth1UserHandler(config.API_KEY, config.API_SECRET_KEY)
            auth.set_access_token(config.ACCESS_TOKEN, config.ACCESS_TOKEN_SECRET)
            self._sync_api = API(auth, wait_on_rate_limit=True)

            logger.debug("Sync API client created successfully")

        except Exception as e:
            logger.error(
                "Failed to initialize Twitter clients",
                extra={"error_type": type(e).__name__},
                exc_info=True,
            )
            raise TwitterClientError(
                "Failed to initialize Twitter API clients",
                context={
                    "config_keys_present": bool(
                        config.API_KEY and config.API_SECRET_KEY
                    )
                },
                original_exception=e,
            )

    @retry_sync_in_async_wrapper
    @async_timed("media_upload")
    async def _upload_media(self, image_content_str: str):
        """Upload media to Twitter with comprehensive logging."""
        logger.debug("Starting media upload")

        try:
            image_content = base64.b64decode(image_content_str)
            image_size = len(image_content)

            logger.debug(
                "Media decoded successfully",
                extra={
                    "original_base64_size": len(image_content_str),
                    "decoded_image_size": image_size,
                },
            )

            if image_size > 5 * 1024 * 1024:  # 5MB limit
                raise TwitterMediaUploadError(
                    "Image size exceeds 5MB limit",
                    media_size=image_size,
                    context={"limit_bytes": 5 * 1024 * 1024},
                )

            image_file = io.BytesIO(image_content)
            image_file.name = "image.png"

            logger.debug("Uploading media via sync API")

            media = await anyio.to_thread.run_sync(
                lambda: self._sync_api.media_upload(
                    filename=image_file.name, file=image_file
                )
            )

            logger.info(
                "Media uploaded successfully",
                extra={"media_id": media.media_id, "media_size": image_size},
            )

            return media

        except Exception as e:
            logger.error(
                "Media upload failed",
                extra={
                    "error_type": type(e).__name__,
                    "image_size": len(image_content_str)
                    if "image_content_str" in locals()
                    else None,
                },
                exc_info=True,
            )

            if isinstance(e, TwitterMediaUploadError):
                raise
            else:
                raise TwitterMediaUploadError(
                    f"Media upload failed: {str(e)}", original_exception=e
                )

    @retry_async_wrapper
    @async_timed("create_tweet")
    async def create_tweet(
        self,
        text: str,
        image_content_str: str | None = None,
        poll_options: list[str] | None = None,
        poll_duration: int | None = None,
        in_reply_to_tweet_id: str | None = None,
        quote_tweet_id: str | None = None,
    ):
        """Create a new tweet with comprehensive logging and error handling."""
        logger.info(
            "Creating tweet",
            extra={
                "text_length": len(text),
                "has_media": bool(image_content_str),
                "has_poll": bool(poll_options),
                "is_reply": bool(in_reply_to_tweet_id),
                "is_quote": bool(quote_tweet_id),
                "poll_options_count": len(poll_options) if poll_options else 0,
            },
        )

        try:
            media_ids = []
            if image_content_str and self.config.media_upload_enabled:
                logger.debug("Media upload requested")
                async with async_operation_timer("tweet_media_upload"):
                    media = await self._upload_media(image_content_str)
                    media_ids.append(media.media_id)
                    logger.debug(f"Media ID added: {media.media_id}")

            poll_params = {}
            if poll_options:
                logger.debug(f"Setting up poll with {len(poll_options)} options")

                if (
                    len(poll_options) < 2
                    or len(poll_options) > self.config.poll_max_options
                ):
                    raise TwitterValidationError(
                        f"Poll must have 2-{self.config.poll_max_options} options",
                        context={
                            "provided_options": len(poll_options),
                            "max_allowed": self.config.poll_max_options,
                        },
                    )

                if (
                    not poll_duration
                    or not 5 <= poll_duration <= self.config.poll_max_duration
                ):
                    raise TwitterValidationError(
                        f"Poll duration must be 5-{self.config.poll_max_duration} minutes",
                        context={
                            "provided_duration": poll_duration,
                            "max_allowed": self.config.poll_max_duration,
                        },
                    )

                poll_params = {
                    "poll_options": poll_options,
                    "poll_duration_minutes": poll_duration,
                }

                logger.debug(
                    "Poll configured",
                    extra={
                        "poll_options": poll_options,
                        "poll_duration_minutes": poll_duration,
                    },
                )

            # Truncate text if needed
            final_text = text[: self.config.max_tweet_length]
            if len(text) > self.config.max_tweet_length:
                logger.warning(
                    f"Tweet text truncated from {len(text)} to {self.config.max_tweet_length} characters"
                )

            logger.debug("Sending tweet to Twitter API")

            response = await self.client.create_tweet(
                text=final_text,
                media_ids=media_ids or None,
                in_reply_to_tweet_id=in_reply_to_tweet_id,
                quote_tweet_id=quote_tweet_id,
                **poll_params,
            )

            tweet_id = response.data["id"]

            logger.info(
                "Tweet created successfully",
                extra={
                    "tweet_id": tweet_id,
                    "final_text_length": len(final_text),
                    "media_count": len(media_ids),
                },
            )

            return tweet_id

        except Exception as e:
            logger.error(
                "Tweet creation failed",
                extra={"error_type": type(e).__name__},
                exc_info=True,
            )

            # Re-raise our custom exceptions
            if isinstance(e, (TwitterAPIError, TwitterMediaUploadError)):
                raise

            # Map external exceptions
            if isinstance(e, TweepyException):
                raise map_tweepy_error(e, context={"operation": "create_tweet"})
            else:
                raise TwitterAPIError(
                    f"Failed to create tweet: {str(e)}", original_exception=e
                )

    @retry_async_wrapper
    @async_timed("retweet_tweet")
    async def retweet_tweet(self, tweet_id: str):
        """Retweet an existing tweet with comprehensive logging."""
        logger.info("Retweeting tweet", extra={"tweet_id": tweet_id})

        try:
            await self.client.retweet(tweet_id=tweet_id)

            logger.info("Tweet retweeted successfully", extra={"tweet_id": tweet_id})

            return f"Successfully retweet post {tweet_id}"

        except Exception as e:
            logger.error(
                "Failed to retweet tweet",
                extra={"tweet_id": tweet_id, "error_type": type(e).__name__},
                exc_info=True,
            )

            if isinstance(e, TweepyException):
                raise map_tweepy_error(
                    e, context={"operation": "retweet", "tweet_id": tweet_id}
                )
            else:
                raise TwitterAPIError(
                    f"Failed to retweet tweet {tweet_id}: {str(e)}",
                    original_exception=e,
                )

    @retry_async_wrapper
    @async_timed("get_user_tweets")
    async def get_user_tweets(self, user_id: str, max_results: int = 10):
        """Retrieve recent tweets with comprehensive logging."""
        logger.info(
            "Retrieving user tweets",
            extra={"user_id": user_id, "max_results": max_results},
        )

        try:
            tweets = await self.client.get_users_tweets(
                id=user_id,
                max_results=max_results,
                tweet_fields=["id", "text", "created_at"],
            )

            tweet_count = len(tweets.data) if tweets and tweets.data else 0

            logger.info(
                "User tweets retrieved successfully",
                extra={"user_id": user_id, "tweets_retrieved": tweet_count},
            )

            return tweets

        except Exception as e:
            logger.error(
                "Failed to retrieve user tweets",
                extra={"user_id": user_id, "error_type": type(e).__name__},
                exc_info=True,
            )

            # Provide detailed guidance for common auth issues
            if "401" in str(e) or "Unauthorized" in str(e):
                logger.error(
                    "Twitter API 401 Unauthorized - Common causes:",
                    extra={
                        "possible_causes": [
                            "Twitter app doesn't have 'Read' permissions",
                            "App needs Twitter API v2 'tweet.read' scope",
                            "Access tokens need regeneration after permission changes",
                            "Elevated access required for reading other users' tweets",
                        ]
                    },
                )

            if isinstance(e, TweepyException):
                raise map_tweepy_error(
                    e, context={"operation": "get_user_tweets", "user_id": user_id}
                )
            else:
                raise TwitterAPIError(
                    f"Failed to get user tweets for {user_id}: {str(e)}",
                    original_exception=e,
                )

    @retry_async_wrapper
    @async_timed("follow_user")
    async def follow_user(self, user_id: str):
        """Follow another Twitter user with comprehensive logging."""
        logger.info("Following user", extra={"user_id": user_id})

        try:
            await self.client.follow_user(user_id=user_id)

            logger.info("User followed successfully", extra={"user_id": user_id})

            return f"Successfully followed user: {user_id}"

        except Exception as e:
            logger.error(
                "Failed to follow user",
                extra={"user_id": user_id, "error_type": type(e).__name__},
                exc_info=True,
            )

            if isinstance(e, TweepyException):
                raise map_tweepy_error(
                    e, context={"operation": "follow_user", "user_id": user_id}
                )
            else:
                raise TwitterAPIError(
                    f"Failed to follow user {user_id}: {str(e)}", original_exception=e
                )

    @retry_async_wrapper
    @async_timed("get_trends")
    async def get_trends(
        self, countries: list[str], max_trends: int = 50
    ) -> dict[str, list[str]]:
        """Retrieve trending topics with comprehensive logging."""
        logger.info(
            "Retrieving trends",
            extra={"countries": countries, "max_trends_per_country": max_trends},
        )

        trends_result: dict[str, list[str]] = {}
        woeid_by_country = {
            "Worldwide": 1,
            "Algeria": 23424740,
            "Argentina": 23424747,
            "Australia": 23424748,
            "Austria": 23424750,
            "Bahrain": 23424753,
            "Belgium": 23424757,
            "Belarus": 23424765,
            "Brazil": 23424768,
            "Canada": 23424775,
            "Chile": 23424782,
            "China": 23424781,
            "Colombia": 23424787,
            "Dominican Republic": 23424800,
            "Ecuador": 23424801,
            "Egypt": 23424802,
            "Ireland": 23424803,
            "France": 23424819,
            "Germany": 23424829,
            "Ghana": 23424824,
            "Greece": 23424833,
            "Guatemala": 23424834,
            "Indonesia": 23424846,
            "India": 23424848,
            "Italy": 23424853,
            "Japan": 23424856,
            "Jordan": 23424860,
            "Kenya": 23424863,
            "South Korea": 23424868,
            "Kuwait": 23424870,
            "Lebanon": 23424873,
            "Latvia": 23424874,
            "Oman": 23424898,
            "Malaysia": 23424901,
            "Mexico": 23424900,
            "Netherlands": 23424909,
            "Norway": 23424910,
            "Nigeria": 23424908,
            "New Zealand": 23424916,
            "Pakistan": 23424922,
            "Poland": 23424923,
            "Panama": 23424924,
            "Portugal": 23424925,
            "Qatar": 23424930,
            "Russia": 23424936,
            "Saudi Arabia": 23424938,
            "South Africa": 23424942,
            "Singapore": 23424948,
            "Spain": 23424950,
            "Sweden": 23424954,
            "Switzerland": 23424957,
            "Thailand": 23424960,
            "Turkey": 23424969,
            "United Arab Emirates": 23424738,
            "Ukraine": 23424976,
            "United Kingdom": 23424975,
            "United States": 23424977,
            "Venezuela": 23424982,
            "Vietnam": 23424984,
        }

        bearer_token = getattr(self.config, "BEARER_TOKEN", None) or os.getenv(
            "BEARER_TOKEN"
        )
        if not bearer_token:
            raise TwitterAPIError(
                "Bearer token not configured for trends endpoint",
                error_code="TWITTER_CONFIG_ERROR",
            )

        headers = {"Authorization": f"Bearer {bearer_token}"}
        timeout = aiohttp.ClientTimeout(total=30)

        try:
            async with aiohttp.ClientSession(
                timeout=timeout, connector=aiohttp.TCPConnector(ssl=self.ssl_context)
            ) as session:
                for country in countries:
                    country_logger = get_logger(
                        f"{__name__}.get_trends", country=country
                    )

                    if country not in woeid_by_country:
                        country_logger.warning(
                            f"WOEID not found for country: {country}"
                        )
                        trends_result[country] = [
                            f"Error: WOEID not found for country {country}"
                        ]
                        continue

                    woeid = woeid_by_country[country]
                    url = f"https://api.twitter.com/2/trends/by/woeid/{woeid}"
                    params = {"max_trends": max_trends}

                    country_logger.debug(
                        f"Fetching trends for {country}",
                        extra={"woeid": woeid, "url": url},
                    )

                    try:
                        async with async_operation_timer(
                            f"get_trends.{country}",
                            context={"country": country, "woeid": woeid},
                        ):
                            async with session.get(
                                url, headers=headers, params=params
                            ) as resp:
                                if resp.status != 200:
                                    error_text = await resp.text()
                                    country_logger.error(
                                        f"Trends API returned error for {country}",
                                        extra={
                                            "status_code": resp.status,
                                            "error_text": error_text[:200],
                                        },
                                    )
                                    trends_result[country] = [
                                        f"Error: {resp.status} {error_text[:100]}"
                                    ]
                                    continue

                                data = await resp.json()
                                trends = [
                                    t.get("trend_name")
                                    for t in data.get("data", [])
                                    if isinstance(t, dict) and t.get("trend_name")
                                ]

                                trends_result[country] = trends
                                country_logger.info(
                                    f"Retrieved {len(trends)} trends for {country}"
                                )

                    except Exception as country_error:
                        country_logger.error(
                            f"Error retrieving trends for {country}",
                            extra={"error_type": type(country_error).__name__},
                            exc_info=True,
                        )
                        trends_result[country] = [
                            f"Error retrieving trends: {str(country_error)}"
                        ]

            logger.info(
                "Trends retrieval completed",
                extra={
                    "countries_requested": len(countries),
                    "countries_successful": len(
                        [
                            c
                            for c, trends in trends_result.items()
                            if not any("Error:" in str(t) for t in trends)
                        ]
                    ),
                    "total_trends_retrieved": sum(
                        len(trends)
                        for trends in trends_result.values()
                        if not any("Error:" in str(t) for t in trends)
                    ),
                },
            )

            return trends_result

        except Exception as e:
            logger.error(
                "Trends retrieval failed",
                extra={"error_type": type(e).__name__},
                exc_info=True,
            )

            if isinstance(e, aiohttp.ClientError):
                raise map_aiohttp_error(e, context={"operation": "get_trends"})
            else:
                raise TwitterAPIError(
                    f"Failed to retrieve trends: {str(e)}", original_exception=e
                )

    @retry_async_wrapper
    @async_timed("search_hashtag")
    async def search_hashtag(self, hashtag: str, max_results: int = 10) -> list[str]:
        """Search recent tweets containing a hashtag with comprehensive logging."""
        if not hashtag.startswith("#"):
            hashtag = f"#{hashtag}"

        max_results = max(10, min(max_results, 100))

        logger.info(
            "Searching hashtag", extra={"hashtag": hashtag, "max_results": max_results}
        )

        try:
            resp = await self.client.search_recent_tweets(
                query=hashtag,
                max_results=max_results,
                tweet_fields=["id", "text", "public_metrics", "created_at"],
                sort_order="relevancy",
            )

            if not resp or not resp.data:
                logger.info(f"No tweets found for hashtag {hashtag}")
                return []

            tweets = resp.data
            tweet_texts = [t.text for t in tweets]

            logger.info(
                "Hashtag search completed",
                extra={"hashtag": hashtag, "tweets_found": len(tweet_texts)},
            )

            return tweet_texts

        except Exception as e:
            logger.error(
                "Hashtag search failed",
                extra={"hashtag": hashtag, "error_type": type(e).__name__},
                exc_info=True,
            )

            if isinstance(e, TweepyException):
                raise map_tweepy_error(
                    e, context={"operation": "search_hashtag", "hashtag": hashtag}
                )
            else:
                raise TwitterAPIError(
                    f"Failed to search hashtag {hashtag}: {str(e)}",
                    original_exception=e,
                )

    @retry_async_wrapper
    @async_timed("initialize_client")
    async def initialize(self):
        """Initialize and test the Twitter client connection with comprehensive logging."""
        logger.info("Initializing Twitter client connection")

        try:
            user = await self.client.get_me()
            username = user.data["username"] if user and user.data else "Unknown"

            logger.info(
                "Twitter client authenticated successfully",
                extra={
                    "authenticated_user": username,
                    "user_id": user.data.get("id") if user and user.data else None,
                },
            )

            return self

        except Exception as e:
            logger.error(
                "Twitter client authentication failed",
                extra={"error_type": type(e).__name__},
                exc_info=True,
            )

            if isinstance(e, TweepyException):
                raise map_tweepy_error(e, context={"operation": "initialize"})
            else:
                raise TwitterAuthenticationError(
                    f"Failed to authenticate Twitter client: {str(e)}",
                    original_exception=e,
                )


# Global client management with enhanced logging
_twitter_client: AsyncTwitterClient | None = None
_client_lock = asyncio.Lock()


@async_timed("get_twitter_client")
async def get_twitter_client() -> AsyncTwitterClient:
    """Get or create the global Twitter client instance with comprehensive logging."""
    global _twitter_client

    if _twitter_client is not None:
        logger.debug("Returning existing Twitter client instance")
        return _twitter_client

    async with _client_lock:
        if _twitter_client is None:
            logger.info("Creating new AsyncTwitterClient instance")

            try:
                from .config import TwitterConfig

                config = TwitterConfig()

                logger.debug(
                    "Twitter configuration loaded",
                    extra={
                        "media_upload_enabled": config.media_upload_enabled,
                        "max_tweet_length": config.max_tweet_length,
                        "has_api_key": bool(config.API_KEY),
                        "has_bearer_token": bool(config.BEARER_TOKEN),
                    },
                )

                client = AsyncTwitterClient(config=config)
                _twitter_client = await client.initialize()

                logger.info(
                    "Global Twitter client instance created and initialized successfully"
                )

            except Exception as e:
                logger.error(
                    "Failed to create global Twitter client",
                    extra={"error_type": type(e).__name__},
                    exc_info=True,
                )
                raise

        return _twitter_client
