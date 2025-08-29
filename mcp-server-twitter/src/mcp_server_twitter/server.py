import json
import os
import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from pydantic import ValidationError

from mcp_server_twitter.twitter import AsyncTwitterClient, get_twitter_client
from mcp_server_twitter.logging_config import get_logger
from mcp_server_twitter.errors import (
    TwitterMCPError, 
    TwitterValidationError, 
    map_tweepy_error,
    map_aiohttp_error
)
from mcp_server_twitter.metrics import (
    async_timed, 
    async_operation_timer,
    get_metrics_collector,
    get_health_checker
)
from mcp_server_twitter.schemas import (
    CreateTweetRequest,
    GetUserTweetsRequest,
    FollowUserRequest,
    RetweetTweetRequest,
    GetTrendsRequest,
    SearchHashtagRequest,
)

# Initialize structured logger
logger = get_logger(__name__)

# --- Enhanced Lifespan Management --- #
@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[dict[str, Any]]:
    """Manage server startup/shutdown with enhanced logging and monitoring."""
    logger.info("Server startup initiated")
    
    # Start metrics logging task if enabled
    metrics_task = None
    if os.getenv("ENABLE_METRICS", "true").lower() in ("true", "1", "yes"):
        metrics_interval = int(os.getenv("METRICS_LOG_INTERVAL", "300"))  # 5 minutes default
        metrics_task = asyncio.create_task(periodic_metrics_logging(metrics_interval))
        logger.info(f"Metrics logging enabled with {metrics_interval}s interval")
    
    try:
        # Initialize Twitter client with timing
        async with async_operation_timer("twitter_client_init"):
            logger.info("Lifespan: Initializing Twitter client...")
            twitter_client: AsyncTwitterClient = await get_twitter_client()
            logger.info("Lifespan: Twitter client initialized successfully")

        # Log initial health status
        health_checker = get_health_checker()
        health_status = health_checker.get_health_status()
        logger.info(
            "Server startup completed",
            extra={
                'startup_health': health_status,
                'client_type': type(twitter_client).__name__
            }
        )
        
        yield {"twitter_client": twitter_client}

    except Exception as init_err:
        logger.error(
            "FATAL: Server startup failed",
            extra={
                'error_type': type(init_err).__name__,
                'error_message': str(init_err)
            },
            exc_info=True
        )
        raise init_err

    finally:
        logger.info("Server shutdown initiated")
        
        # Cancel metrics task
        if metrics_task:
            metrics_task.cancel()
            try:
                await metrics_task
            except asyncio.CancelledError:
                pass
        
        # Log final metrics summary
        metrics_collector = get_metrics_collector()
        metrics_collector.log_summary()
        
        logger.info("Lifespan: Shutdown cleanup completed")

async def periodic_metrics_logging(interval_seconds: int):
    """Periodically log metrics summary."""
    while True:
        try:
            await asyncio.sleep(interval_seconds)
            
            metrics_collector = get_metrics_collector()
            health_checker = get_health_checker()
            
            # Log metrics summary
            metrics_collector.log_summary()
            
            # Log health status
            health_status = health_checker.get_health_status()
            logger.info(
                f"Health check: {health_status['status']}",
                extra={'health_status': health_status}
            )
            
        except asyncio.CancelledError:
            logger.info("Metrics logging task cancelled")
            break
        except Exception as e:
            logger.error(
                "Error in periodic metrics logging",
                extra={'error_type': type(e).__name__},
                exc_info=True
            )

# --- MCP Server Initialization --- #
mcp_server = FastMCP("twitter-server", lifespan=app_lifespan)

# --- Tool Definitions with Enhanced Logging --- #

@mcp_server.tool()
@async_timed("create_tweet")
async def create_tweet(
    ctx: Context,
    request: CreateTweetRequest,
) -> str:
    """Create a tweet with comprehensive logging and error handling."""
    operation_logger = get_logger(
        f"{__name__}.create_tweet",
        operation="create_tweet",
        text_length=len(request.text),
        has_image=bool(request.image_content_str),
        has_poll=bool(request.poll_options),
        is_reply=bool(request.in_reply_to_tweet_id),
        is_quote=bool(request.quote_tweet_id)
    )
    
    operation_logger.info(
        "Tweet creation requested",
        extra={
            'text_preview': request.text[:50] + "..." if len(request.text) > 50 else request.text,
            'poll_options_count': len(request.poll_options) if request.poll_options else 0,
            'poll_duration': request.poll_duration
        }
    )
    
    client = ctx.request_context.lifespan_context["twitter_client"]

    try:
        # Input validation with detailed logging
        if request.image_content_str:
            operation_logger.debug("Validating image content")
            image_size = len(request.image_content_str.encode("utf-8"))
            operation_logger.debug(f"Image size: {image_size} bytes")
            
            if image_size > 5_000_000:
                raise TwitterValidationError(
                    "Image content too large (max 5MB)",
                    field_name="image_content_str",
                    field_value=f"{image_size} bytes",
                    context={"max_size_bytes": 5_000_000}
                )

        operation_logger.debug("Calling Twitter API to create tweet")
        
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
            operation_logger.error(f"Tweet creation returned error: {result}")
            raise TwitterMCPError(f"Tweet creation failed: {result}")
        
        tweet_id = str(result)
        operation_logger.info(
            "Tweet created successfully",
            extra={'tweet_id': tweet_id}
        )
        
        return f"Tweet created successfully with ID: {tweet_id}"

    except TwitterMCPError as e:
        operation_logger.warning(f"A known Twitter MCP error occurred: {e.message}", extra={'error_code': e.error_code})
        raise ToolError(str(e)) from e
    except ValidationError as e:
        operation_logger.warning("Input validation failed", extra={'errors': e.errors()})
        raise ToolError(f"Invalid input: {e}") from e
    except Exception as e:
        operation_logger.error(
            "An unexpected error occurred during tweet creation",
            extra={'error_type': type(e).__name__},
            exc_info=True
        )
        raise ToolError(f"An unexpected error occurred: {e}") from e

@mcp_server.tool()
@async_timed("get_user_tweets")
async def get_user_tweets(
    ctx: Context, 
    request: GetUserTweetsRequest
) -> str:
    """Retrieve user tweets with comprehensive logging."""
    operation_logger = get_logger(
        f"{__name__}.get_user_tweets",
        operation="get_user_tweets",
        user_count=len(request.user_ids),
        max_results=request.max_results
    )
    
    operation_logger.info(
        "User tweets retrieval requested",
        extra={
            'user_ids': request.user_ids,
            'max_results_per_user': request.max_results
        }
    )
    
    client = ctx.request_context.lifespan_context["twitter_client"]

    try:
        tweets_dict: dict[str, list[str]] = {}
        
        for uid in request.user_ids:
            user_logger = get_logger(
                f"{__name__}.get_user_tweets",
                operation="get_user_tweets",
                user_id=uid
            )
            
            user_logger.debug(f"Fetching tweets for user {uid}")
            
            try:
                async with async_operation_timer(
                    f"get_user_tweets.user_{uid}", context={"user_id": uid}
                ):
                    resp = await client.get_user_tweets(
                        user_id=uid, max_results=request.max_results
                    )

                    if resp and resp.get("data"):
                        tweets_dict[uid] = [t["text"] for t in resp["data"]]
                        user_logger.info(
                            f"Retrieved {len(resp["data"])} tweets for user {uid}"
                        )
                    else:
                        tweets_dict[uid] = []
                        user_logger.warning(f"No tweets found for user {uid}")

            except Exception as e:
                error_message = f"Error retrieving tweets for user {uid}: {e}"
                operation_logger.error(
                    error_message,
                    extra={"error_type": type(e).__name__},
                    exc_info=True,
                )
                if "401 Unauthorized" in str(e):
                    tweets_dict[uid] = [f"Error: Unauthorized access. Twitter API permissions may be insufficient to read tweets for user {uid}"]
                elif "403 Forbidden" in str(e):
                    tweets_dict[uid] = [f"Error: Access forbidden for user {uid}. Account may be private or protected"]
                elif "404 User Not Found" in str(e):
                    tweets_dict[uid] = [f"Error: User {uid} not found or account is private/suspended"]
                else:
                    tweets_dict[uid] = [error_message]
                continue

        operation_logger.info(
            "User tweets retrieval completed",
            extra={
                'successful_users': len([uid for uid, tweets in tweets_dict.items() if not any('Error:' in tweet for tweet in tweets)]),
                'failed_users': len([uid for uid, tweets in tweets_dict.items() if any('Error:' in tweet for tweet in tweets)]),
                'total_tweets': sum(len(tweets) for tweets in tweets_dict.values() if not any('Error:' in tweet for tweet in tweets))
            }
        )
        
        return json.dumps(tweets_dict, ensure_ascii=False, indent=2)

    except ValidationError as e:
        operation_logger.warning("Input validation failed", extra={'errors': e.errors()})
        raise ToolError(f"Invalid input: {e}") from e
    except Exception as e:
        operation_logger.error(
            "Unexpected error during user tweets retrieval",
            extra={'error_type': type(e).__name__},
            exc_info=True
        )
        raise ToolError(f"Error retrieving tweets: {str(e)}")

@mcp_server.tool()
@async_timed("follow_user")
async def follow_user(ctx: Context, request: FollowUserRequest) -> str:
    """Follow user with comprehensive logging."""
    operation_logger = get_logger(
        f"{__name__}.follow_user",
        operation="follow_user",
        target_user_id=request.user_id
    )
    
    operation_logger.info(f"User follow requested for user {request.user_id}")
    
    client = ctx.request_context.lifespan_context["twitter_client"]

    try:
        operation_logger.debug(f"Calling Twitter API to follow user {request.user_id}")
        response = await client.follow_user(request.user_id)
        
        operation_logger.info(
            f"Successfully followed user {request.user_id}",
            extra={'api_response': str(response)}
        )
        
        return f"Following user: {response}"

    except TwitterMCPError as e:
        operation_logger.error(
            f"A known Twitter MCP error occurred while following user {request.user_id}",
            extra={'error_type': type(e).__name__, 'error_code': e.error_code},
            exc_info=True
        )
        raise ToolError(f"Error following user {request.user_id}: {str(e)}") from e
    except ValidationError as e:
        operation_logger.warning("Input validation failed", extra={'errors': e.errors()})
        raise ToolError(f"Invalid input: {e}") from e
    except Exception as e:
        operation_logger.error(
            f"Unexpected error following user {request.user_id}",
            extra={'error_type': type(e).__name__},
            exc_info=True
        )
        raise ToolError(f"An unexpected error occurred while following user {request.user_id}: {str(e)}") from e

@mcp_server.tool()
@async_timed("retweet_tweet")
async def retweet_tweet(ctx: Context, request: RetweetTweetRequest) -> str:
    """Retweet with comprehensive logging."""
    operation_logger = get_logger(
        f"{__name__}.retweet_tweet",
        operation="retweet_tweet",
        tweet_id=request.tweet_id
    )
    
    operation_logger.info(f"Retweet requested for tweet {request.tweet_id}")
    
    client = ctx.request_context.lifespan_context["twitter_client"]

    try:
        operation_logger.debug(f"Calling Twitter API to retweet {request.tweet_id}")
        response = await client.retweet_tweet(request.tweet_id)
        
        operation_logger.info(
            f"Successfully retweeted {request.tweet_id}",
            extra={'api_response': str(response)}
        )
        
        return f"Retweeting tweet: {response}"

    except TwitterMCPError as e:
        operation_logger.error(
            f"A known Twitter MCP error occurred while retweeting {request.tweet_id}",
            extra={'error_type': type(e).__name__, 'error_code': e.error_code},
            exc_info=True
        )
        raise ToolError(f"Error retweeting {request.tweet_id}: {str(e)}") from e
    except ValidationError as e:
        operation_logger.warning("Input validation failed", extra={'errors': e.errors()})
        raise ToolError(f"Invalid input: {e}") from e
    except Exception as e:
        operation_logger.error(
            f"Unexpected error retweeting {request.tweet_id}",
            extra={'error_type': type(e).__name__},
            exc_info=True
        )
        raise ToolError(f"An unexpected error occurred while retweeting {request.tweet_id}: {str(e)}") from e

@mcp_server.tool()
@async_timed("get_trends")
async def get_trends(ctx: Context, request: GetTrendsRequest) -> str:
    """Get trends with comprehensive logging."""
    operation_logger = get_logger(
        f"{__name__}.get_trends",
        operation="get_trends",
        country_count=len(request.countries),
        max_trends=request.max_trends
    )
    
    operation_logger.info(
        "Trends retrieval requested",
        extra={
            'countries': request.countries,
            'max_trends_per_country': request.max_trends
        }
    )
    
    client = ctx.request_context.lifespan_context["twitter_client"]

    try:
        operation_logger.debug("Calling Twitter API to retrieve trends")
        trends = await client.get_trends(
            countries=request.countries, 
            max_trends=request.max_trends
        )
        
        operation_logger.info(
            "Trends retrieved successfully",
            extra={
                'countries_processed': len(trends),
                'total_trends': sum(len(country_trends) for country_trends in trends.values() if isinstance(country_trends, list))
            }
        )
        
        return json.dumps(trends, ensure_ascii=False, indent=2)
        
    except TwitterMCPError as e:
        operation_logger.error(
            "A known Twitter MCP error occurred while retrieving trends",
            extra={'error_type': type(e).__name__, 'error_code': e.error_code},
            exc_info=True
        )
        raise ToolError(f"Error retrieving trends: {str(e)}") from e
    except ValidationError as e:
        operation_logger.warning("Input validation failed", extra={'errors': e.errors()})
        raise ToolError(f"Invalid input: {e}") from e
    except Exception as e:
        operation_logger.error(
            "Unexpected error while retrieving trends",
            extra={'error_type': type(e).__name__},
            exc_info=True
        )
        raise ToolError(f"An unexpected error occurred while retrieving trends: {str(e)}") from e

@mcp_server.tool()
@async_timed("search_hashtag")
async def search_hashtag(ctx: Context, request: SearchHashtagRequest) -> str:
    """Search hashtag with comprehensive logging."""
    operation_logger = get_logger(
        f"{__name__}.search_hashtag",
        operation="search_hashtag",
        hashtag=request.hashtag,
        max_results=request.max_results
    )
    
    operation_logger.info(
        f"Hashtag search requested for #{request.hashtag}",
        extra={'max_results': request.max_results}
    )
    
    client = ctx.request_context.lifespan_context["twitter_client"]

    try:
        operation_logger.debug(f"Calling Twitter API to search hashtag #{request.hashtag}")
        tweets = await client.search_hashtag(
            hashtag=request.hashtag, 
            max_results=request.max_results
        )
        
        operation_logger.info(
            f"Hashtag search completed for #{request.hashtag}",
            extra={'tweets_found': len(tweets)}
        )
        
        return json.dumps(tweets, ensure_ascii=False, indent=2)
        
    except TwitterMCPError as e:
        operation_logger.error(
            f"A known Twitter MCP error occurred while searching hashtag #{request.hashtag}",
            extra={'error_type': type(e).__name__, 'error_code': e.error_code},
            exc_info=True
        )
        raise ToolError(f"Error searching hashtag: {str(e)}") from e
    except ValidationError as e:
        operation_logger.warning("Input validation failed", extra={'errors': e.errors()})
        raise ToolError(f"Invalid input: {e}") from e
    except Exception as e:
        operation_logger.error(
            f"Unexpected error searching hashtag #{request.hashtag}",
            extra={'error_type': type(e).__name__},
            exc_info=True
        )
        raise ToolError(f"An unexpected error occurred while searching for a hashtag: {str(e)}") from e

# --- Health Check Endpoint --- #
async def get_health_status() -> dict:
    """Get server health status and metrics."""
    health_checker = get_health_checker()
    health_status = health_checker.get_health_status()
    
    logger.debug("Health status requested", extra={'health_status': health_status})
    
    return health_status

async def get_metrics() -> dict:
    """Get server performance metrics."""
    metrics_collector = get_metrics_collector()
    metrics = metrics_collector.get_all_metrics()
    
    logger.debug("Metrics requested", extra={'metrics_summary': metrics})
    
    return metrics