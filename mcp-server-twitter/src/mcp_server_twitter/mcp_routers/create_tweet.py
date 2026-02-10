import logging

from fastapi import APIRouter, Depends
from fastmcp.exceptions import ToolError
from pydantic import ValidationError

from mcp_server_twitter.dependencies import get_twitter_client_dep
from mcp_server_twitter.errors import TwitterMCPError, TwitterValidationError
from mcp_server_twitter.logging_config import get_logger
from mcp_server_twitter.metrics import async_timed
from mcp_server_twitter.schemas import CreateTweetRequest

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/create-tweet",
    tags=["Twitter"],
    operation_id="twitter_create_tweet",
)
@async_timed("create_tweet")
async def create_tweet(
    create_request: CreateTweetRequest,
    client: AsyncTwitterClient = Depends(get_twitter_client_dep),
) -> str:
    """Create a tweet with comprehensive logging and error handling."""
    operation_logger = get_logger(
        f"{__name__}.create_tweet",
        operation="create_tweet",
        text_length=len(create_request.text),
        has_image=bool(create_request.image_content_str),
        has_poll=bool(create_request.poll_options),
        is_reply=bool(create_request.in_reply_to_tweet_id),
        is_quote=bool(create_request.quote_tweet_id),
    )

    operation_logger.info(
        "Tweet creation requested",
        extra={
            "text_preview": create_request.text[:50] + "..."
            if len(create_request.text) > 50
            else create_request.text,
            "poll_options_count": len(create_request.poll_options)
            if create_request.poll_options
            else 0,
            "poll_duration": create_request.poll_duration,
        },
    )

    try:
        # Input validation with detailed logging
        if create_request.image_content_str:
            operation_logger.debug("Validating image content")
            image_size = len(create_request.image_content_str.encode("utf-8"))
            operation_logger.debug(f"Image size: {image_size} bytes")

            if image_size > 5_000_000:
                raise TwitterValidationError(
                    "Image content too large (max 5MB)",
                    field_name="image_content_str",
                    field_value=f"{image_size} bytes",
                    context={"max_size_bytes": 5_000_000},
                )

        operation_logger.debug("Calling Twitter API to create tweet")

        # Call Twitter client with validated data
        result = await client.create_tweet(
            text=create_request.text,
            image_content_str=create_request.image_content_str,
            poll_options=create_request.poll_options,
            poll_duration=create_request.poll_duration,
            in_reply_to_tweet_id=create_request.in_reply_to_tweet_id,
            quote_tweet_id=create_request.quote_tweet_id,
        )

        if isinstance(result, str) and ("Error" in result or "error" in result):
            operation_logger.error(f"Tweet creation returned error: {result}")
            raise TwitterMCPError(f"Tweet creation failed: {result}")

        tweet_id = str(result)
        operation_logger.info(
            "Tweet created successfully", extra={"tweet_id": tweet_id}
        )

        return f"Tweet created successfully with ID: {tweet_id}"

    except TwitterMCPError as e:
        operation_logger.warning(
            f"A known Twitter MCP error occurred: {e.message}",
            extra={"error_code": e.error_code},
        )
        raise ToolError(str(e)) from e
    except ValidationError as e:
        operation_logger.warning(
            "Input validation failed", extra={"errors": e.errors()}
        )
        raise ToolError(f"Invalid input: {e}") from e
    except Exception as e:
        operation_logger.error(
            "An unexpected error occurred during tweet creation",
            extra={"error_type": type(e).__name__},
            exc_info=True,
        )
        raise ToolError(f"An unexpected error occurred: {e}") from e
