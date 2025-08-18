import json
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError

from mcp_server_twitter.twitter import AsyncTwitterClient, get_twitter_client

from mcp_server_twitter.schemas import (
    CreateTweetRequest,
    GetUserTweetsRequest,
    FollowUserRequest,
    RetweetTweetRequest,
    GetTrendsRequest,
    SearchHashtagRequest,
)

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
async def create_tweet(
    ctx: Context,
    request: CreateTweetRequest,
) -> str:
    client = ctx.request_context.lifespan_context["twitter_client"]

    try:
        # Check Base64 image size (max ~5MB)
        if request.image_content_str:
            image_size = len(request.image_content_str.encode("utf-8"))
            if image_size > 5_000_000:
                raise ToolError("Image content too large (max 5MB)")

        # Call Twitter client with validated data
        result = await client.create_tweet(
            text=request.text,
            image_content_str=request.image_content_str,
            poll_options=request.poll_options,
            poll_duration=request.poll_duration,
            in_reply_to_tweet_id=request.in_reply_to_tweet_id,
            quote_tweet_id=request.quote_tweet_id,
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
async def get_user_tweets(
    ctx: Context, 
    request: GetUserTweetsRequest
) -> str:
    client = ctx.request_context.lifespan_context["twitter_client"]

    try:
        tweets_dict: dict[str, list[str]] = {}

        for uid in request.user_ids:
            try:
                resp = await client.get_user_tweets(
                    user_id=uid, max_results=request.max_results
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
async def follow_user(ctx: Context, request: FollowUserRequest) -> str:
    client = ctx.request_context.lifespan_context["twitter_client"]

    try:
        # Follow another Twitter user by their user ID.
        response = await client.follow_user(request.user_id)
        return f"Following user: {response}"

    except Exception as follow_error:
        msg = str(follow_error)
        if "404" in msg or "Not Found" in msg:
            raise ToolError(f"User {request.user_id} not found")
        elif "403" in msg or "Forbidden" in msg:
            raise ToolError(
                "Cannot follow user. Account may be private or already followed"
            )
        elif "401" in msg or "Unauthorized" in msg:
            raise ToolError("Unauthorized. Check Twitter API permissions")
        else:
            raise ToolError(f"Error following user {request.user_id}: {msg}")


@mcp_server.tool()
async def retweet_tweet(ctx: Context, request: RetweetTweetRequest) -> str:
    client = ctx.request_context.lifespan_context["twitter_client"]

    try:
        # Retweet an existing tweet on behalf of the authenticated user.
        response = await client.retweet_tweet(request.tweet_id)
        return f"Retweeting tweet: {response}"

    except Exception as retweet_error:
        msg = str(retweet_error)
        if "404" in msg or "Not Found" in msg:
            raise ToolError(
                f"Tweet {request.tweet_id} not found or has been deleted"
            )
        elif "403" in msg or "Forbidden" in msg:
            raise ToolError("Cannot retweet. Already retweeted or tweet is private")
        elif "401" in msg or "Unauthorized" in msg:
            raise ToolError("Unauthorized. Check Twitter API permissions")
        else:
            raise ToolError(f"Error retweeting {request.tweet_id}: {msg}")


@mcp_server.tool()
async def get_trends(ctx: Context, request: GetTrendsRequest) -> str:
    client = ctx.request_context.lifespan_context["twitter_client"]

    try:
        # Retrieve trending topics for each provided WOEID.
        trends = await client.get_trends(countries=request.countries, max_trends=request.max_trends)
        return json.dumps(trends, ensure_ascii=False, indent=2)
    except Exception as e:
        raise ToolError(f"Error retrieving trends: {str(e)}")


@mcp_server.tool()
async def search_hashtag(ctx: Context, request: SearchHashtagRequest) -> str:
    client = ctx.request_context.lifespan_context["twitter_client"]

    try:
        # Search recent tweets containing a hashtag and return the most popular ones.
        tweets = await client.search_hashtag(hashtag=request.hashtag, max_results=request.max_results)
        return json.dumps(tweets, ensure_ascii=False, indent=2)
    except Exception as e:
        raise ToolError(f"Error searching hashtag: {str(e)}")
