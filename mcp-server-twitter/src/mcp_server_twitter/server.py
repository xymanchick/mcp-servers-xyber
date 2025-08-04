import json
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any
from pydantic import ValidationError as PydanticValidationError

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError


from .twitter import AsyncTwitterClient, get_twitter_client

from .schemas import (
    CreateTweetRequest,
    GetUserTweetsRequest,
    FollowUserRequest,
    RetweetTweetRequest,
    GetTrendsRequest,
    SearchHashtagRequest,
)

logger = logging.getLogger(__name__)


# --- Custom Exceptions --- #
class ValidationError(ToolError):
    """Custom exception for input validation failures."""

    def __init__(self, message: str, code: str = "VALIDATION_ERROR"):
        super().__init__(message, code=code)
        self.status_code = 400


# --- Lifespan Management --- #
@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[dict[str, Any]]:
    """Manage server startup/shutdown. Initializes the Twitter client."""
    logger.info("Lifespan: Initializing Twitter client...")

    try:
        # Initialize Twitter client
        twitter_client: AsyncTwitterClient = await get_twitter_client()

        logger.info("Lifespan: Twitter client initialized successfully")
        yield {"twitter_client": twitter_client}

    except Exception as init_err:
        logger.error(
            f"FATAL: Lifespan initialization failed: {init_err}", exc_info=True
        )
        raise init_err

    finally:
        logger.info("Lifespan: Shutdown cleanup completed")


# --- MCP Server Initialization --- #
mcp_server = FastMCP("twitter-server", lifespan=app_lifespan)


# --- Tool Definitions --- #


@mcp_server.tool()
async def create_tweet(
    ctx: Context,
    text: str,
    image_content_str: str | None = None,
    poll_options: list[str] | None = None,
    poll_duration: int | None = None,
    in_reply_to_tweet_id: str | None = None,
    quote_tweet_id: str | None = None,
) -> str:
    client = ctx.request_context.lifespan_context["twitter_client"]

    try:
        # Validate input
        CreateTweetRequest(
            text=text,
            image_content_str=image_content_str,
            poll_options=poll_options,
            poll_duration=poll_duration,
            in_reply_to_tweet_id=in_reply_to_tweet_id,
            quote_tweet_id=quote_tweet_id,
        )

        # Create tweet
        result = await client.create_tweet(
            text=text,
            image_content_str=image_content_str,
            poll_options=poll_options,
            poll_duration=poll_duration,
            in_reply_to_tweet_id=in_reply_to_tweet_id,
            quote_tweet_id=quote_tweet_id,
        )

        # Check if the result is an error string or a tweet ID
        if isinstance(result, str) and ("Error" in result or "error" in result):
            raise ToolError(f"Tweet creation failed: {result}")
        else:
            return f"Tweet created successfully with ID: {result}"

    except PydanticValidationError as ve:
        logger.warning(f"Validation error: {ve}")
        error_details = "; ".join(
            f"{err['loc'][0]}: {err['msg']}" for err in ve.errors()
        )
        raise ValidationError(f"Invalid parameters: {error_details}")
    except ToolError:
        raise
    except Exception as e:
        error_msg = str(e)
        if "403" in error_msg or "Forbidden" in error_msg:
            raise ToolError(
                "Tweet creation forbidden. Check content policy or API permissions"
            )
        elif "401" in error_msg or "Unauthorized" in error_msg:
            raise ToolError(
                "Unauthorized. Check Twitter API credentials and permissions"
            )
        elif "duplicate" in error_msg.lower():
            raise ToolError("Duplicate tweet. This content has already been posted")
        else:
            raise ToolError(f"Error creating tweet: {error_msg}")


@mcp_server.tool()
async def get_user_tweets(
    ctx: Context, user_ids: list[str], max_results: int = 10
) -> str:
    client = ctx.request_context.lifespan_context["twitter_client"]

    try:
        # Validate input
        GetUserTweetsRequest(
            user_ids=user_ids,
            max_results=max_results,
        )

        tweets_dict: dict[str, list[str]] = {}

        for uid in user_ids:
            try:
                resp = await client.get_user_tweets(
                    user_id=uid, max_results=max_results
                )

                if resp and resp.data:
                    tweets_dict[uid] = [t.text for t in resp.data]
                else:
                    tweets_dict[uid] = []

            except Exception as user_error:
                # Handle individual user errors gracefully
                error_msg = str(user_error)
                if "401" in error_msg or "Unauthorized" in error_msg:
                    tweets_dict[uid] = [
                        f"Error: Unauthorized access. Twitter API permissions may be insufficient to read tweets for user {uid}"
                    ]
                elif "404" in error_msg or "Not Found" in error_msg:
                    tweets_dict[uid] = [
                        f"Error: User {uid} not found or account is private/suspended"
                    ]
                elif "403" in error_msg or "Forbidden" in error_msg:
                    tweets_dict[uid] = [
                        f"Error: Access forbidden for user {uid}. Account may be private or protected"
                    ]
                else:
                    tweets_dict[uid] = [
                        f"Error retrieving tweets for user {uid}: {error_msg}"
                    ]
                logger.warning(f"Failed to get tweets for user {uid}: {error_msg}")

        return json.dumps(tweets_dict, ensure_ascii=False, indent=2)

    except PydanticValidationError as ve:
        logger.warning(f"Validation error: {ve}")
        error_details = "; ".join(
            f"{err['loc'][0]}: {err['msg']}" for err in ve.errors()
        )
        raise ValidationError(f"Invalid parameters: {error_details}")
    except Exception as e:
        logger.error(f"Unexpected error in get_user_tweets: {str(e)}", exc_info=True)
        raise ToolError(f"Error retrieving tweets: {str(e)}")


@mcp_server.tool()
async def follow_user(ctx: Context, user_id: str) -> str:
    client = ctx.request_context.lifespan_context["twitter_client"]

    try:
        # Validate input
        FollowUserRequest(user_id=user_id)

        # Follow another Twitter user by their user ID.
        response = await client.follow_user(user_id)
        return f"Following user: {response}"

    except PydanticValidationError as ve:
        logger.warning(f"Validation error: {ve}")
        error_details = "; ".join(
            f"{err['loc'][0]}: {err['msg']}" for err in ve.errors()
        )
        raise ValidationError(f"Invalid parameters: {error_details}")
    except Exception as follow_error:
        error_msg = str(follow_error)
        if "404" in error_msg or "Not Found" in error_msg:
            raise ToolError(f"User {user_id} not found")
        elif "403" in error_msg or "Forbidden" in error_msg:
            raise ToolError(
                f"Cannot follow user {user_id}. Account may be private or you may already be following them"
            )
        elif "401" in error_msg or "Unauthorized" in error_msg:
            raise ToolError(
                "Unauthorized. Check Twitter API permissions for following users"
            )
        else:
            raise ToolError(f"Error following user {user_id}: {error_msg}")


@mcp_server.tool()
async def retweet_tweet(ctx: Context, tweet_id: str) -> str:
    client = ctx.request_context.lifespan_context["twitter_client"]

    try:
        # Validate input
        RetweetTweetRequest(tweet_id=tweet_id)

        # Retweet an existing tweet on behalf of the authenticated user.
        response = await client.retweet_tweet(tweet_id)
        return f"Retweeting tweet: {response}"

    except PydanticValidationError as ve:
        logger.warning(f"Validation error: {ve}")
        error_details = "; ".join(
            f"{err['loc'][0]}: {err['msg']}" for err in ve.errors()
        )
        raise ValidationError(f"Invalid parameters: {error_details}")
    except Exception as retweet_error:
        error_msg = str(retweet_error)
        if "404" in error_msg or "Not Found" in error_msg:
            raise ToolError(f"Tweet {tweet_id} not found or has been deleted")
        elif "403" in error_msg or "Forbidden" in error_msg:
            raise ToolError(
                f"Cannot retweet {tweet_id}. Tweet may be private or you may have already retweeted it"
            )
        elif "401" in error_msg or "Unauthorized" in error_msg:
            raise ToolError(
                "Unauthorized. Check Twitter API permissions for retweeting"
            )
        else:
            raise ToolError(f"Error retweeting {tweet_id}: {error_msg}")


@mcp_server.tool()
async def get_trends(ctx: Context, countries: list[str], max_trends: int = 50) -> str:
    client = ctx.request_context.lifespan_context["twitter_client"]

    try:
        # Validate input
        GetTrendsRequest(
            countries=countries,
            max_trends=max_trends,
        )

        # Retrieve trending topics for each provided WOEID.
        trends = await client.get_trends(countries=countries, max_trends=max_trends)
        return json.dumps(trends, ensure_ascii=False, indent=2)
    except PydanticValidationError as ve:
        logger.warning(f"Validation error: {ve}")
        error_details = "; ".join(
            f"{err['loc'][0]}: {err['msg']}" for err in ve.errors()
        )
        raise ValidationError(f"Invalid parameters: {error_details}")
    except Exception as e:
        logger.error(f"Error retrieving trends: {str(e)}", exc_info=True)
        raise ToolError(f"Error retrieving trends: {str(e)}")


@mcp_server.tool()
async def search_hashtag(ctx: Context, hashtag: str, max_results: int = 10) -> str:
    client = ctx.request_context.lifespan_context["twitter_client"]

    try:
        # Validate input
        SearchHashtagRequest(
            hashtag=hashtag,
            max_results=max_results,
        )

        # Search recent tweets containing a hashtag and return the most popular ones.
        tweets = await client.search_hashtag(hashtag=hashtag, max_results=max_results)
        return json.dumps(tweets, ensure_ascii=False, indent=2)
    except PydanticValidationError as ve:
        logger.warning(f"Validation error: {ve}")
        error_details = "; ".join(
            f"{err['loc'][0]}: {err['msg']}" for err in ve.errors()
        )
        raise ValidationError(f"Invalid parameters: {error_details}")
    except Exception as e:
        logger.error(f"Error searching hashtag: {str(e)}", exc_info=True)
        raise ToolError(f"Error searching hashtag: {str(e)}")
