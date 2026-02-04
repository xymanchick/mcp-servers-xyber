import json
import logging
from fastapi import APIRouter, Request
from fastmcp.exceptions import ToolError
from pydantic import ValidationError

from mcp_server_twitter.logging_config import get_logger
from mcp_server_twitter.metrics import async_timed, async_operation_timer
from mcp_server_twitter.schemas import GetUserTweetsRequest

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/get-user-tweets",
    tags=["Twitter"],
    operation_id="twitter_get_user_tweets",
)
@async_timed("get_user_tweets")
async def get_user_tweets(
    get_request: GetUserTweetsRequest,
    request: Request,
) -> str:
    """Retrieve user tweets with comprehensive logging."""
    operation_logger = get_logger(
        f"{__name__}.get_user_tweets",
        operation="get_user_tweets",
        user_count=len(get_request.user_ids),
        max_results=get_request.max_results
    )

    operation_logger.info(
        "User tweets retrieval requested",
        extra={
            'user_ids': get_request.user_ids,
            'max_results_per_user': get_request.max_results
        }
    )

    client = request.app.state.twitter_client

    try:
        tweets_dict: dict[str, list[str]] = {}

        for uid in get_request.user_ids:
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
                        user_id=uid, max_results=get_request.max_results
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
