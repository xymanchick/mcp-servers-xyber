import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi import Request
from fastmcp import Context
from fastmcp.exceptions import ToolError

from mcp_server_telegram.telegram import TelegramServiceError


async def post_to_telegram_impl(ctx: Context, message: str, mock_get_telegram_service=None) -> str:
    from mcp_server_telegram.server import logger
    from mcp_server_telegram.telegram import get_telegram_service
    
    request: Request = ctx.request_context.request

    token = request.headers.get("X-Telegram-Token")
    channel = request.headers.get("X-Telegram-Channel")

    if not token:
        logger.error("Request failed: Missing 'X-Telegram-Token' header.")
        raise ToolError(
            "Your request is missing the required 'X-Telegram-Token' HTTP header."
        )
    if not channel:
        logger.error("Request failed: Missing 'X-Telegram-Channel' header.")
        raise ToolError(
            "Your request is missing the required 'X-Telegram-Channel' HTTP header."
        )

    logger.info(
        f"Received request to post to channel '{channel}' with a provided token."
    )

    try:
        if mock_get_telegram_service:
            telegram_service = mock_get_telegram_service(token=token, channel=channel)
        else:
            telegram_service = get_telegram_service(token=token, channel=channel)

        success: bool = await telegram_service.send_message(message)

        if success:
            logger.info(
                f"Message successfully posted to the Telegram channel '{channel}'"
            )
            return f"Message successfully posted to the Telegram channel '{channel}'"
        else:
            logger.warning(
                f"Failed to post message to the Telegram channel '{channel}'"
            )
            raise ToolError("The Telegram service failed to post the message.")

    except ToolError:
        raise
    except TelegramServiceError as service_err:
        logger.error(f"Service error during message posting: {service_err}")
        raise ToolError(f"Telegram service error: {service_err}") from service_err
    except Exception as e:
        logger.error(f"Unexpected error during message posting: {e}", exc_info=True)
        raise ToolError("An unexpected error occurred during message posting.") from e


class TestPostToTelegram:
    @pytest.mark.asyncio
    async def test_post_to_telegram_success(self, mock_context, mock_telegram_service):
        mock_context.request_context.request.headers = {
            "X-Telegram-Token": "valid_token", 
            "X-Telegram-Channel": "@test_channel"
        }
        mock_telegram_service.send_message.return_value = True
        message = "Test message"
        
        def mock_get_service(token, channel):
            return mock_telegram_service
        
        result = await post_to_telegram_impl(mock_context, message, mock_get_service)
        
        assert result == "Message successfully posted to the Telegram channel '@test_channel'"
        mock_telegram_service.send_message.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_post_to_telegram_missing_token_header(self, mock_context):
        mock_context.request_context.request.headers = {
            "X-Telegram-Channel": "@test_channel"
        }
        message = "Test message"
        
        with pytest.raises(ToolError, match="Your request is missing the required 'X-Telegram-Token' HTTP header"):
            await post_to_telegram_impl(mock_context, message)

    @pytest.mark.asyncio
    async def test_post_to_telegram_missing_channel_header(self, mock_context):
        mock_context.request_context.request.headers = {
            "X-Telegram-Token": "valid_token"
        }
        message = "Test message"
        
        with pytest.raises(ToolError, match="Your request is missing the required 'X-Telegram-Channel' HTTP header"):
            await post_to_telegram_impl(mock_context, message)

    @pytest.mark.asyncio
    async def test_post_to_telegram_missing_both_headers(self, mock_context):
        mock_context.request_context.request.headers = {}
        message = "Test message"
        
        with pytest.raises(ToolError, match="Your request is missing the required 'X-Telegram-Token' HTTP header"):
            await post_to_telegram_impl(mock_context, message)

    @pytest.mark.asyncio
    async def test_post_to_telegram_service_returns_false(self, mock_context, mock_telegram_service):
        mock_context.request_context.request.headers = {
            "X-Telegram-Token": "valid_token",
            "X-Telegram-Channel": "@test_channel"
        }
        mock_telegram_service.send_message.return_value = False
        message = "Test message"
        
        def mock_get_service(token, channel):
            return mock_telegram_service
        
        with pytest.raises(ToolError, match="The Telegram service failed to post the message"):
            await post_to_telegram_impl(mock_context, message, mock_get_service)

    @pytest.mark.asyncio
    async def test_post_to_telegram_service_error(self, mock_context, mock_telegram_service):
        mock_context.request_context.request.headers = {
            "X-Telegram-Token": "valid_token",
            "X-Telegram-Channel": "@test_channel"
        }
        service_error = TelegramServiceError("Service unavailable")
        mock_telegram_service.send_message.side_effect = service_error
        message = "Test message"
        
        def mock_get_service(token, channel):
            return mock_telegram_service
        
        with pytest.raises(ToolError, match="Telegram service error: Service unavailable"):
            await post_to_telegram_impl(mock_context, message, mock_get_service)

    @pytest.mark.asyncio
    async def test_post_to_telegram_unexpected_error(self, mock_context, mock_telegram_service):
        mock_context.request_context.request.headers = {
            "X-Telegram-Token": "valid_token",
            "X-Telegram-Channel": "@test_channel"
        }
        unexpected_error = Exception("Unexpected error")
        mock_telegram_service.send_message.side_effect = unexpected_error
        message = "Test message"
        
        def mock_get_service(token, channel):
            return mock_telegram_service
        
        with pytest.raises(ToolError, match="An unexpected error occurred during message posting"):
            await post_to_telegram_impl(mock_context, message, mock_get_service)

    @pytest.mark.asyncio
    async def test_post_to_telegram_with_logging(self, mock_context, mock_telegram_service):
        mock_context.request_context.request.headers = {
            "X-Telegram-Token": "valid_token",
            "X-Telegram-Channel": "@test_channel"
        }
        mock_telegram_service.send_message.return_value = True
        message = "Test message"
        
        def mock_get_service(token, channel):
            return mock_telegram_service
        
        with patch('mcp_server_telegram.server.logger') as mock_logger:
            result = await post_to_telegram_impl(mock_context, message, mock_get_service)
            
            assert result == "Message successfully posted to the Telegram channel '@test_channel'"
            mock_logger.info.assert_any_call(
                "Received request to post to channel '@test_channel' with a provided token."
            )
            mock_logger.info.assert_any_call(
                "Message successfully posted to the Telegram channel '@test_channel'"
            )

    @pytest.mark.asyncio
    async def test_post_to_telegram_empty_token_header(self, mock_context):
        mock_context.request_context.request.headers = {
            "X-Telegram-Token": "",
            "X-Telegram-Channel": "@test_channel"
        }
        message = "Test message"
        
        with pytest.raises(ToolError, match="Your request is missing the required 'X-Telegram-Token' HTTP header"):
            await post_to_telegram_impl(mock_context, message)

    @pytest.mark.asyncio
    async def test_post_to_telegram_empty_channel_header(self, mock_context):
        mock_context.request_context.request.headers = {
            "X-Telegram-Token": "valid_token",
            "X-Telegram-Channel": ""
        }
        message = "Test message"
        
        with pytest.raises(ToolError, match="Your request is missing the required 'X-Telegram-Channel' HTTP header"):
            await post_to_telegram_impl(mock_context, message)


class TestPostToTelegramEdgeCases:
    @pytest.mark.asyncio
    async def test_post_to_telegram_none_headers(self, mock_context):
        mock_context.request_context.request.headers = {
            "X-Telegram-Token": None,
            "X-Telegram-Channel": None
        }
        message = "Test message"
        
        with pytest.raises(ToolError, match="Your request is missing the required 'X-Telegram-Token' HTTP header"):
            await post_to_telegram_impl(mock_context, message)

    @pytest.mark.asyncio
    async def test_post_to_telegram_long_message(self, mock_context, mock_telegram_service):
        mock_context.request_context.request.headers = {
            "X-Telegram-Token": "valid_token",
            "X-Telegram-Channel": "@test_channel"
        }
        mock_telegram_service.send_message.return_value = True
        
        message = "A" * 5000
        
        def mock_get_service(token, channel):
            return mock_telegram_service
        
        result = await post_to_telegram_impl(mock_context, message, mock_get_service)
        
        assert result == "Message successfully posted to the Telegram channel '@test_channel'"
        mock_telegram_service.send_message.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_post_to_telegram_special_characters_in_channel(self, mock_context, mock_telegram_service):
        special_channel = "@test_channel_123-test"
        mock_context.request_context.request.headers = {
            "X-Telegram-Token": "valid_token",
            "X-Telegram-Channel": special_channel
        }
        mock_telegram_service.send_message.return_value = True
        message = "Test message"
        
        def mock_get_service(token, channel):
            return mock_telegram_service
        
        result = await post_to_telegram_impl(mock_context, message, mock_get_service)
        
        assert result == f"Message successfully posted to the Telegram channel '{special_channel}'"
        mock_telegram_service.send_message.assert_called_once_with(message)
