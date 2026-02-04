import logging
from fastapi import APIRouter, Request
from fastmcp.exceptions import ToolError
from pydantic import ValidationError

from mcp_server_twitter.logging_config import get_logger
from mcp_server_twitter.metrics import async_timed
from mcp_server_twitter.schemas import RetweetTweetRequest
from mcp_server_twitter.errors import TwitterMCPError

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/retweet-tweet",
    tags=["Twitter"],
    operation_id="twitter_retweet_tweet",
)
@async_timed("retweet_tweet")
async def retweet_tweet(
    retweet_request: RetweetTweetRequest,
    request: Request,
) -> str:
    """Retweet with comprehensive logging."""
    operation_logger = get_logger(
        f"{__name__}.retweet_tweet",
        operation="retweet_tweet",
        tweet_id=retweet_request.tweet_id
    )

    operation_logger.info(f"Retweet requested for tweet {retweet_request.tweet_id}")

    client = request.app.state.twitter_client

    try:
        operation_logger.debug(f"Calling Twitter API to retweet {retweet_request.tweet_id}")
        response = await client.retweet_tweet(retweet_request.tweet_id)

        operation_logger.info(
            f"Successfully retweeted {retweet_request.tweet_id}",
            extra={'api_response': str(response)}
        )

        return f"Retweeting tweet: {response}"

    except TwitterMCPError as e:
        operation_logger.error(
            f"A known Twitter MCP error occurred while retweeting {retweet_request.tweet_id}",
            extra={'error_type': type(e).__name__, 'error_code': e.error_code},
            exc_info=True
        )
        raise ToolError(f"Error retweeting {retweet_request.tweet_id}: {str(e)}") from e
    except ValidationError as e:
        operation_logger.warning("Input validation failed", extra={'errors': e.errors()})
        raise ToolError(f"Invalid input: {e}") from e
    except Exception as e:
        operation_logger.error(
            f"Unexpected error retweeting {retweet_request.tweet_id}",
            extra={'error_type': type(e).__name__},
            exc_info=True
        )
        raise ToolError(f"An unexpected error occurred while retweeting {retweet_request.tweet_id}: {str(e)}") from e
