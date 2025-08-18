import json
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from pydantic import ValidationError

from .schemas import (
    CreateTweetInput,
    FollowUserInput,
    GetTrendsInput,
    GetUserTweetsInput,
    RetweetTweetInput,
    SearchHashtagInput,
)
from .twitter import AsyncTwitterClient, get_twitter_client

logger = logging.getLogger(__name__)


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
async def create_tweet(ctx: Context, tool_input: dict) -> str:
    """
    Create a new tweet with optional media, polls, replies or quotes.

    Args:
        tool_input: A dictionary of input parameters, validated using Pydantic. Keys:
            - text (str): The text content of the tweet (1–280 characters).
            - image_content_str (optional, str): A Base64-encoded string of image data to attach as media. Optional.
            - poll_options (optional, list[str]): A list of 2 to 4 options to include in a poll.
            - poll_duration (optional, int): Duration of the poll in minutes (5–10080).
            - in_reply_to_tweet_id (optional, str): The ID of an existing tweet to reply to.
            - quote_tweet_id (optional, str): The ID of an existing tweet to quote.

    Returns:
        str: Success message with tweet ID or error message.
    """

    client = ctx.request_context.lifespan_context["twitter_client"]

    try:
        # Validate input
        validated_data = CreateTweetInput(**tool_input)

        # Check Base64 image size (max ~5MB)
        if validated_data.image_content_str:
            image_size = len(validated_data.image_content_str.encode("utf-8"))
            if image_size > 5_000_000:
                raise ToolError("Image content too large (max 5MB)", status_code=413)

    except ValidationError as e:
        # Return structured error with HTTP 400
        raise ToolError(f"Invalid input: {e.errors()}", status_code=400)

    try:
        # Call Twitter client with validated data
        result = await client.create_tweet(
            text=validated_data.text,
            image_content_str=validated_data.image_content_str,
            poll_options=validated_data.poll_options,
            poll_duration=validated_data.poll_duration,
            in_reply_to_tweet_id=validated_data.in_reply_to_tweet_id,
            quote_tweet_id=validated_data.quote_tweet_id,
        )

        if isinstance(result, str) and ("Error" in result or "error" in result):
            raise ToolError(f"Tweet creation failed: {result}")
        return f"Tweet created successfully with ID: {result}"

    except ToolError:
        raise
    except Exception as e:
        msg = str(e)
        if "403" in msg or "Forbidden" in msg:
            raise ToolError(
                "Tweet creation forbidden. Check content policy or API permissions"
            )
        elif "401" in msg or "Unauthorized" in msg:
            raise ToolError("Unauthorized. Check Twitter API credentials")
        elif "duplicate" in msg.lower():
            raise ToolError("Duplicate tweet. This content has already been posted")
        else:
            raise ToolError(f"Error creating tweet: {msg}")


@mcp_server.tool()
async def get_user_tweets(ctx: Context, tool_input: dict) -> str:
    """
    Retrieve recent tweets posted by a list of users.

    Args:
        tool_input: A dict with keys:
            - user_ids: list of user IDs to fetch tweets for
            - max_results: (optional) number of tweets per user (1–100)

    Returns:
        JSON string mapping user IDs to tweet texts or error messages.
    """
    client = ctx.request_context.lifespan_context["twitter_client"]

    try:
        validated_data = GetUserTweetsInput(**tool_input)
    except ValidationError as e:
        raise ToolError(e.errors())

    try:
        tweets_dict: dict[str, list[str]] = {}

        for uid in validated_data.user_ids:
            try:
                resp = await client.get_user_tweets(
                    user_id=uid, max_results=validated_data.max_results
                )
                if resp and resp.data:
                    tweets_dict[uid] = [t.text for t in resp.data]
                else:
                    tweets_dict[uid] = []

            except Exception as user_error:
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

        return json.dumps(tweets_dict, ensure_ascii=False, indent=2)

    except Exception as e:
        raise ToolError(f"Error retrieving tweets: {str(e)}")


@mcp_server.tool()
async def follow_user(ctx: Context, tool_input: dict) -> str:
    """
    Follow another Twitter user by their user ID.

    Args:
        tool_input: A dict with "user_id": str

    Returns:
        Success message confirming the follow.
    """
    client = ctx.request_context.lifespan_context["twitter_client"]

    try:
        validated_data = FollowUserInput(**tool_input)
    except ValidationError as e:
        raise ToolError(e.errors())

    try:
        response = await client.follow_user(validated_data.user_id)
        return f"Following user: {response}"

    except Exception as follow_error:
        msg = str(follow_error)
        if "404" in msg or "Not Found" in msg:
            raise ToolError(f"User {validated_data.user_id} not found")
        elif "403" in msg or "Forbidden" in msg:
            raise ToolError(
                "Cannot follow user. Account may be private or already followed"
            )
        elif "401" in msg or "Unauthorized" in msg:
            raise ToolError("Unauthorized. Check Twitter API permissions")
        else:
            raise ToolError(f"Error following user {validated_data.user_id}: {msg}")


@mcp_server.tool()
async def retweet_tweet(ctx: Context, tool_input: dict) -> str:
    """
    Retweet an existing tweet on behalf of the authenticated user.

    Args:
        tool_input: A dict with "tweet_id": str

    Returns:
        Success message confirming the retweet.
    """
    client = ctx.request_context.lifespan_context["twitter_client"]

    try:
        validated_data = RetweetTweetInput(**tool_input)
    except ValidationError as e:
        raise ToolError(e.errors())

    try:
        response = await client.retweet_tweet(validated_data.tweet_id)
        return f"Retweeting tweet: {response}"

    except Exception as retweet_error:
        msg = str(retweet_error)
        if "404" in msg or "Not Found" in msg:
            raise ToolError(
                f"Tweet {validated_data.tweet_id} not found or has been deleted"
            )
        elif "403" in msg or "Forbidden" in msg:
            raise ToolError("Cannot retweet. Already retweeted or tweet is private")
        elif "401" in msg or "Unauthorized" in msg:
            raise ToolError("Unauthorized. Check Twitter API permissions")
        else:
            raise ToolError(f"Error retweeting {validated_data.tweet_id}: {msg}")


@mcp_server.tool()
async def get_trends(ctx: Context, tool_input: dict) -> str:
    """
    Retrieve trending topics for each provided country.

    Args:
        tool_input: A dict with keys:
            - countries: list of country names (required)
            - max_trends: int, optional (default 50, range 1–50)

    Returns:
        JSON string mapping countries to list of trending topics
    """
    client = ctx.request_context.lifespan_context["twitter_client"]

    try:
        validated = GetTrendsInput(**tool_input)
    except ValidationError as e:
        raise ToolError(e.errors())

    try:
        trends = await client.get_trends(
            countries=validated.countries, max_trends=validated.max_trends
        )
        return json.dumps(trends, ensure_ascii=False, indent=2)
    except Exception as e:
        raise ToolError(f"Error retrieving trends: {str(e)}")


@mcp_server.tool()
async def search_hashtag(ctx: Context, tool_input: dict) -> str:
    """
    Search recent tweets containing a hashtag and return the most popular ones.

    Args:
        tool_input: Dict with:
            - hashtag (str): The hashtag to search for
            - max_results (int): Optional, number of tweets to return (10–100)

    Returns:
        JSON string with matched tweet texts
    """
    client = ctx.request_context.lifespan_context["twitter_client"]

    try:
        validated = SearchHashtagInput(**tool_input)
    except ValidationError as e:
        raise ToolError(e.errors())

    try:
        tweets = await client.search_hashtag(
            hashtag=validated.hashtag, max_results=validated.max_results
        )
        return json.dumps(tweets, ensure_ascii=False, indent=2)
    except Exception as e:
        raise ToolError(f"Error searching hashtag: {str(e)}")
