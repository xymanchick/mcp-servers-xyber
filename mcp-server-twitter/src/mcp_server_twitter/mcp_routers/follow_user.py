import logging

from fastapi import APIRouter, Depends
from fastmcp.exceptions import ToolError
from pydantic import ValidationError

from mcp_server_twitter.dependencies import get_twitter_client_dep
from mcp_server_twitter.errors import TwitterMCPError
from mcp_server_twitter.logging_config import get_logger
from mcp_server_twitter.metrics import async_timed
from mcp_server_twitter.schemas import FollowUserRequest

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/follow-user",
    tags=["Twitter"],
    operation_id="twitter_follow_user",
)
@async_timed("follow_user")
async def follow_user(
    follow_request: FollowUserRequest,
    client: AsyncTwitterClient = Depends(get_twitter_client_dep),
) -> str:
    """Follow user with comprehensive logging."""
    operation_logger = get_logger(
        f"{__name__}.follow_user",
        operation="follow_user",
        target_user_id=follow_request.user_id,
    )

    operation_logger.info(f"User follow requested for user {follow_request.user_id}")

    try:
        operation_logger.debug(
            f"Calling Twitter API to follow user {follow_request.user_id}"
        )
        response = await client.follow_user(follow_request.user_id)

        operation_logger.info(
            f"Successfully followed user {follow_request.user_id}",
            extra={"api_response": str(response)},
        )

        return f"Following user: {response}"

    except TwitterMCPError as e:
        operation_logger.error(
            f"A known Twitter MCP error occurred while following user {follow_request.user_id}",
            extra={"error_type": type(e).__name__, "error_code": e.error_code},
            exc_info=True,
        )
        raise ToolError(
            f"Error following user {follow_request.user_id}: {str(e)}"
        ) from e
    except ValidationError as e:
        operation_logger.warning(
            "Input validation failed", extra={"errors": e.errors()}
        )
        raise ToolError(f"Invalid input: {e}") from e
    except Exception as e:
        operation_logger.error(
            f"Unexpected error following user {follow_request.user_id}",
            extra={"error_type": type(e).__name__},
            exc_info=True,
        )
        raise ToolError(
            f"An unexpected error occurred while following user {follow_request.user_id}: {str(e)}"
        ) from e
