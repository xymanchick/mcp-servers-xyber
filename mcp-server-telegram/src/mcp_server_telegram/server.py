# mcp_server_telegram/server.py
import logging
from typing import Dict, Any

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from fastapi import Request # <-- CHANGE: Import Request to access headers

from mcp_server_telegram.telegram import (
    get_telegram_service,
    TelegramServiceError,
    TelegramConfigError,
)

logger = logging.getLogger(__name__)

# --- MCP Server Initialization (NO LIFESPAN) --- #
# CHANGE: The lifespan is removed. The server is now stateless at startup.
mcp_server = FastMCP(
    name="telegram",
)

@mcp_server.tool()
async def post_to_telegram(
    ctx: Context,
    message: str, # <-- The tool is now very simple! It only takes the message.
) -> str:
    """
    Posts a message to a pre-configured Telegram channel.
    The API Token and Channel ID must be provided in the request headers:
    - 'X-Telegram-Token'
    - 'X-Telegram-Channel'
    """
    request: Request = ctx.request_context.request
    
    # --- Get BOTH token and channel from headers ---
    token = request.headers.get("X-Telegram-Token")
    channel = request.headers.get("X-Telegram-Channel")

    # --- Validate that both were provided ---
    if not token:
        logger.error("Request failed: Missing 'X-Telegram-Token' header.")
        raise ToolError("Your request is missing the required 'X-Telegram-Token' HTTP header.")
    if not channel:
        logger.error("Request failed: Missing 'X-Telegram-Channel' header.")
        raise ToolError("Your request is missing the required 'X-Telegram-Channel' HTTP header.")

    logger.info(f"Received request to post to channel '{channel}' with a provided token.")

    try:
        # Get a service instance configured with the user's specific key and channel.
        telegram_service = get_telegram_service(token=token, channel=channel)
        
        success: bool = await telegram_service.send_message(message)
        
        if success:
            logger.info(f"Message successfully posted to the Telegram channel '{channel}'")
            return f"Message successfully posted to the Telegram channel '{channel}'"
        else:
            logger.warning(f"Failed to post message to the Telegram channel '{channel}'")
            raise ToolError("The Telegram service failed to post the message.")
    
    except TelegramServiceError as service_err:
        logger.error(f"Service error during message posting: {service_err}")
        raise ToolError(f"Telegram service error: {service_err}") from service_err
    
    except Exception as e:
        logger.error(f"Unexpected error during message posting: {e}", exc_info=True)
        raise ToolError("An unexpected error occurred during message posting.") from e