"""
MCP tool for posting messages to Telegram channels.

Main responsibility: Define the post_to_telegram MCP tool that sends messages to configured Telegram channels.
"""

import logging

from fastapi import APIRouter, Header, HTTPException

from mcp_server_telegram.schemas import PostToTelegramRequest
from mcp_server_telegram.telegram import TelegramServiceError, get_telegram_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/post-to-telegram",
    tags=["Telegram"],
    operation_id="telegram_post_to_telegram",
)
async def post_to_telegram(
    request: PostToTelegramRequest,
    x_telegram_token: str = Header(..., alias="X-Telegram-Token"),
    x_telegram_channel: str = Header(..., alias="X-Telegram-Channel"),
) -> str:
    """
    Posts a message to a pre-configured Telegram channel.

    The API Token and Channel ID must be provided in the request headers:
    - 'X-Telegram-Token': Your Telegram bot API token
    - 'X-Telegram-Channel': The channel ID or username (e.g., @channelname)

    Args:
        request: The message content to post
        x_telegram_token: Telegram bot API token (from header)
        x_telegram_channel: Telegram channel ID (from header)

    Returns:
        Success message confirming the post

    Raises:
        HTTPException: If the token or channel is missing, or if posting fails

    """
    logger.info(
        f"Received request to post to channel '{x_telegram_channel}' with a provided token."
    )

    try:
        # Get a service instance configured with the user's specific key and channel
        telegram_service = get_telegram_service(
            token=x_telegram_token, channel=x_telegram_channel
        )

        success: bool = await telegram_service.send_message(request.message)

        if success:
            logger.info(
                f"Message successfully posted to the Telegram channel '{x_telegram_channel}'"
            )
            return f"Message successfully posted to the Telegram channel '{x_telegram_channel}'"
        else:
            logger.warning(
                f"Failed to post message to the Telegram channel '{x_telegram_channel}'"
            )
            raise HTTPException(
                status_code=500,
                detail="The Telegram service failed to post the message.",
            )

    except TelegramServiceError as service_err:
        logger.error(f"Service error during message posting: {service_err}")
        raise HTTPException(
            status_code=500, detail=f"Telegram service error: {service_err}"
        ) from service_err

    except Exception as e:
        logger.error(f"Unexpected error during message posting: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred during message posting.",
        ) from e
