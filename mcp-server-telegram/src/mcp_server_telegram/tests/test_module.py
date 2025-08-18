import asyncio
import pytest
from unittest.mock import Mock, patch
import requests
from requests.exceptions import HTTPError, ConnectionError, Timeout, JSONDecodeError

from mcp_server_telegram.telegram.module import (
    _TelegramService,
    get_telegram_service,
    MAX_MESSAGE_LENGTH,
)
from mcp_server_telegram.telegram.config import (
    TelegramConfig,
    TelegramConfigError,
)


class TestTelegramService:
    def test_init_with_valid_config(self, mock_config):
        service = _TelegramService(mock_config)
        
        assert service.config == mock_config
        assert service.config.token == "test_token"
        assert service.config.channel == "@test_channel"

    def test_init_with_empty_token(self, mock_config_empty_token):
        service = _TelegramService(mock_config_empty_token)
        
        assert service.config.token == ""
        assert service.config.channel == "@test_channel"

    def test_init_with_empty_channel(self, mock_config_empty_channel):
        service = _TelegramService(mock_config_empty_channel)
        
        assert service.config.token == "test_token"
        assert service.config.channel == ""

    @pytest.mark.asyncio
    async def test_send_message_missing_token(self, mock_config_empty_token):
        service = _TelegramService(mock_config_empty_token)
        
        with pytest.raises(TelegramConfigError, match="Telegram token or channel is missing"):
            await service.send_message("test message")

    @pytest.mark.asyncio
    async def test_send_message_missing_channel(self, mock_config_empty_channel):
        service = _TelegramService(mock_config_empty_channel)
        
        with pytest.raises(TelegramConfigError, match="Telegram token or channel is missing"):
            await service.send_message("test message")

    @pytest.mark.asyncio
    async def test_send_message_missing_both(self, mock_config_empty_both):
        service = _TelegramService(mock_config_empty_both)
        
        with pytest.raises(TelegramConfigError, match="Telegram token or channel is missing"):
            await service.send_message("test message")

    @pytest.mark.asyncio
    @patch('mcp_server_telegram.telegram.module.requests.post')
    async def test_send_message_success(self, mock_post, mock_config, mock_success_response):
        # Setup
        service = _TelegramService(mock_config)
        mock_post.return_value = mock_success_response
        
        # Execute
        result = await service.send_message("test message")
        
        # Verify
        assert result is True
        mock_post.assert_called_once()
        
        # Check the call arguments
        call_args = mock_post.call_args
        assert call_args[1]['json']['chat_id'] == "@test_channel"
        assert call_args[1]['json']['text'] == "test message"
        assert call_args[1]['json']['parse_mode'] == "HTML"

    @pytest.mark.asyncio
    @patch('mcp_server_telegram.telegram.module.requests.post')
    async def test_send_message_truncate_long_text(self, mock_post, mock_config, mock_success_response):
        service = _TelegramService(mock_config)
        mock_post.return_value = mock_success_response
        
        # message longer than MAX_MESSAGE_LENGTH
        long_message = "A" * (MAX_MESSAGE_LENGTH + 100)
        
        result = await service.send_message(long_message)
        
        assert result is True
        mock_post.assert_called_once()
        
        call_args = mock_post.call_args
        sent_text = call_args[1]['json']['text']
        assert len(sent_text) <= MAX_MESSAGE_LENGTH + len("... [message truncated]")
        assert sent_text.endswith("... [message truncated]")

    @pytest.mark.asyncio
    @patch('mcp_server_telegram.telegram.module.requests.post')
    async def test_send_message_retry_on_parse_error(self, mock_post, mock_config, 
                                                   mock_400_parse_error_response, mock_success_response):
        service = _TelegramService(mock_config)
        mock_post.side_effect = [mock_400_parse_error_response, mock_success_response]
        
        result = await service.send_message("test message")
        
        assert result is True
        assert mock_post.call_count == 2
        
        first_call = mock_post.call_args_list[0]
        second_call = mock_post.call_args_list[1]
        
        # First call should have HTML initially, but gets modified after 400 error
        # Since the payload is modified in place, we can only check the second call
        assert second_call[1]['json']['parse_mode'] == ""
        assert second_call[1]['json']['chat_id'] == "@test_channel"
        assert second_call[1]['json']['text'] == "test message"

    @pytest.mark.asyncio
    @patch('mcp_server_telegram.telegram.module.requests.post')
    async def test_send_message_400_error_not_parse_related(self, mock_post, mock_config, 
                                                          mock_400_other_error_response):
        service = _TelegramService(mock_config)
        mock_post.return_value = mock_400_other_error_response
        
        result = await service.send_message("test message")
        
        assert result is False
        assert mock_post.call_count == 1  # No retry for non-parse errors

    @pytest.mark.asyncio
    @patch('mcp_server_telegram.telegram.module.requests.post')
    async def test_send_message_http_error(self, mock_post, mock_config):
        service = _TelegramService(mock_config)
        
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = HTTPError(response=mock_response)
        mock_response.json.return_value = {"description": "Unauthorized"}
        mock_post.return_value = mock_response
        
        result = await service.send_message("test message")
        
        assert result is False

    @pytest.mark.asyncio
    @patch('mcp_server_telegram.telegram.module.requests.post')
    async def test_send_message_connection_error(self, mock_post, mock_config):
        service = _TelegramService(mock_config)
        
        mock_post.side_effect = ConnectionError("Network unreachable")
        
        result = await service.send_message("test message")
        
        assert result is False

    @pytest.mark.asyncio
    @patch('mcp_server_telegram.telegram.module.requests.post')
    async def test_send_message_timeout_error(self, mock_post, mock_config):
        service = _TelegramService(mock_config)
        
        mock_post.side_effect = Timeout("Request timeout")
        
        result = await service.send_message("test message")
        
        assert result is False

    @pytest.mark.asyncio
    @patch('mcp_server_telegram.telegram.module.requests.post')
    async def test_send_message_unexpected_error(self, mock_post, mock_config):
        service = _TelegramService(mock_config)
        
        mock_post.side_effect = ValueError("Unexpected error")
        
        result = await service.send_message("test message")
        
        assert result is False


class TestGetTelegramService:
    @patch('mcp_server_telegram.telegram.module.TelegramConfig')
    def test_get_telegram_service_success(self, mock_config_class, mock_config):
        get_telegram_service.cache_clear()
        
        mock_config_class.return_value = mock_config
        
        service = get_telegram_service("test_token", "@test_channel")
        
        assert isinstance(service, _TelegramService)
        assert service.config.token == "test_token"
        assert service.config.channel == "@test_channel"

    @patch('mcp_server_telegram.telegram.module.TelegramConfig')
    def test_get_telegram_service_caching(self, mock_config_class, mock_config):
        get_telegram_service.cache_clear()
        
        mock_config_class.return_value = mock_config
        
        service1 = get_telegram_service("test_token", "@test_channel")
        service2 = get_telegram_service("test_token", "@test_channel")
        
        # Should return the same instance due to caching
        assert service1 is service2

    @patch('mcp_server_telegram.telegram.module.TelegramConfig')
    def test_get_telegram_service_different_params(self, mock_config_class, create_mock_config):
        get_telegram_service.cache_clear()
        
        def side_effect(token, channel):
            return create_mock_config(token=token, channel=channel)
            
        mock_config_class.side_effect = side_effect
        
        service1 = get_telegram_service("token1", "@channel1")
        service2 = get_telegram_service("token2", "@channel2")
        
        # must be different instances
        assert service1 is not service2
        assert service1.config.token == "token1"
        assert service2.config.token == "token2"

    @patch('mcp_server_telegram.telegram.module.TelegramConfig')
    def test_get_telegram_service_config_error(self, mock_config_class):
        get_telegram_service.cache_clear()
        
        mock_config_class.side_effect = ValueError("Invalid configuration")
        
        with pytest.raises(TelegramConfigError, match="Configuration error for Telegram service"):
            get_telegram_service("invalid_token", "invalid_channel")


class TestConstants:
    def test_max_message_length(self):
        assert MAX_MESSAGE_LENGTH == 4000
        assert isinstance(MAX_MESSAGE_LENGTH, int)


class TestTelegramServiceAdditional:
    @pytest.mark.asyncio
    @patch('mcp_server_telegram.telegram.module.requests.post')
    async def test_send_message_http_error_no_json(self, mock_post, mock_config, mock_500_error_response):
        service = _TelegramService(mock_config)
        
        mock_500_error_response.raise_for_status.side_effect = HTTPError(response=mock_500_error_response)
        mock_500_error_response.json.side_effect = JSONDecodeError("No JSON", "", 0)
        mock_post.return_value = mock_500_error_response
        
        result = await service.send_message("test message")
        
        assert result is False

    @pytest.mark.asyncio
    @patch('mcp_server_telegram.telegram.module.requests.post')
    async def test_send_message_400_parse_error_variations(self, mock_post, mock_config, mock_success_response):
        service = _TelegramService(mock_config)
        
        first_response = Mock()
        first_response.status_code = 400
        first_response.json.return_value = {"description": "Bad Request: parse error at position 5"}
        
        mock_post.side_effect = [first_response, mock_success_response]
        
        result = await service.send_message("test <invalid> html")
        
        assert result is True
        assert mock_post.call_count == 2
