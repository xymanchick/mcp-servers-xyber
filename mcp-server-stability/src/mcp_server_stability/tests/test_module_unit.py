import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest


def get_stability_module():
    try:
        from mcp_server_stability.stable_diffusion.config import (
            StableDiffusionClientError, StableDiffusionServerConnectionError)
        from mcp_server_stability.stable_diffusion.module import (
            StabilityService, get_stability_service)

        return (
            StabilityService,
            get_stability_service,
            StableDiffusionClientError,
            StableDiffusionServerConnectionError,
        )
    except ImportError as e:
        pytest.skip(f"Failed to import module: {e}")


class TestStabilityServiceUnit:
    @pytest.fixture(autouse=True)
    def setup(self):
        (
            self.StabilityService,
            self.get_stability_service,
            self.ClientError,
            self.ConnectionError,
        ) = get_stability_module()

    def test_init(self, mock_stability_config):
        service = self.StabilityService(mock_stability_config)

        assert service.api_key == "sk-test-api-key-12345"
        assert (
            service.host == "https://api.stability.ai/v2beta/stable-image/generate/core"
        )
        assert service.client is None

    @pytest.mark.asyncio
    async def test_initialize_client_success(self, mock_stability_config):
        service = self.StabilityService(mock_stability_config)

        with patch("httpx.AsyncClient") as mock_httpx_client:
            mock_client_instance = Mock()
            mock_httpx_client.return_value = mock_client_instance

            await service._initialize_client()

            mock_httpx_client.assert_called_once()
            assert service.client == mock_client_instance

    @pytest.mark.asyncio
    async def test_initialize_client_already_initialized(self, mock_stability_config):
        service = self.StabilityService(mock_stability_config)
        existing_client = Mock()
        service.client = existing_client

        with patch("httpx.AsyncClient") as mock_httpx_client:
            await service._initialize_client()

            mock_httpx_client.assert_not_called()
            assert service.client == existing_client

    @pytest.mark.asyncio
    async def test_initialize_client_failure(self, mock_stability_config):
        service = self.StabilityService(mock_stability_config)

        with patch("httpx.AsyncClient", side_effect=Exception("Connection failed")):
            with pytest.raises(self.ClientError) as exc_info:
                await service._initialize_client()

            assert "Failed to initialize" in str(exc_info.value)
            assert service.client is None

    @pytest.mark.asyncio
    async def test_cleanup_with_client(self, mock_stability_config):
        service = self.StabilityService(mock_stability_config)
        mock_client = AsyncMock()
        service.client = mock_client

        await service.cleanup()

        mock_client.aclose.assert_called_once()
        assert service.client is None

    @pytest.mark.asyncio
    async def test_cleanup_without_client(self, mock_stability_config):
        service = self.StabilityService(mock_stability_config)
        assert service.client is None

        await service.cleanup()
        assert service.client is None

    @pytest.mark.asyncio
    async def test_send_generation_request_success(
        self, mock_stability_config, sample_generation_params, mock_successful_response
    ):
        service = self.StabilityService(mock_stability_config)

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_successful_response

        with patch.object(service, "_initialize_client") as mock_init:
            service.client = mock_client

            response = await service.send_generation_request(sample_generation_params)

            mock_init.assert_called_once()

            mock_client.post.assert_called_once_with(
                service.host, files={"none": ""}, data=sample_generation_params
            )

            assert response == mock_successful_response

    @pytest.mark.asyncio
    async def test_send_generation_request_http_error(self, mock_stability_config):
        service = self.StabilityService(mock_stability_config)

        class MockRequestError(Exception):
            pass

        mock_client = AsyncMock()
        mock_client.post.side_effect = MockRequestError("Network error")

        with patch.object(service, "_initialize_client"):
            service.client = mock_client

            with patch("httpx.RequestError", MockRequestError):
                with pytest.raises(self.ConnectionError) as exc_info:
                    await service.send_generation_request({"prompt": "test"})

                assert "Error during request" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_send_generation_request_api_error(
        self, mock_stability_config, mock_error_response
    ):
        service = self.StabilityService(mock_stability_config)

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_error_response

        with patch.object(service, "_initialize_client"):
            service.client = mock_client

            with pytest.raises(self.ClientError) as exc_info:
                await service.send_generation_request({"prompt": "test"})

            assert "API error: 400" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_multiple_requests_same_client(
        self, mock_stability_config, mock_successful_response
    ):
        service = self.StabilityService(mock_stability_config)

        params1 = {"prompt": "first image"}
        params2 = {"prompt": "second image"}

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_successful_response

        with patch.object(service, "_initialize_client") as mock_init:
            service.client = mock_client

            await service.send_generation_request(params1)
            await service.send_generation_request(params2)

            # Инициализация должна быть вызвана дважды
            assert mock_init.call_count == 2

            # POST должен быть вызван дважды
            assert mock_client.post.call_count == 2


class TestGetStabilityServiceUnit:
    @pytest.fixture(autouse=True)
    def setup(self):
        (
            self.StabilityService,
            self.get_stability_service,
            self.ClientError,
            self.ConnectionError,
        ) = get_stability_module()

    @pytest.mark.asyncio
    async def test_get_stability_service(self):
        with patch(
            "mcp_server_stability.stable_diffusion.module.StableDiffusionClientConfig"
        ) as mock_config_class:
            mock_config = Mock()
            mock_config_class.return_value = mock_config

            service = await self.get_stability_service()

            mock_config_class.assert_called_once()

            assert isinstance(service, self.StabilityService)


class TestStabilityServiceEdgeCases:
    @pytest.fixture(autouse=True)
    def setup(self):
        (
            self.StabilityService,
            self.get_stability_service,
            self.ClientError,
            self.ConnectionError,
        ) = get_stability_module()

    @pytest.mark.asyncio
    async def test_cleanup_during_request(self, mock_stability_config):
        service = self.StabilityService(mock_stability_config)

        mock_client = AsyncMock()
        service.client = mock_client

        # Имитируем длительный запрос
        async def slow_post(*args, **kwargs):
            await service.cleanup()  # Очистка во время запроса
            mock_response = Mock()
            mock_response.is_success = True
            return mock_response

        mock_client.post = slow_post

        with patch.object(service, "_initialize_client"):
            response = await service.send_generation_request({"prompt": "test"})

            assert service.client is None

    @pytest.mark.asyncio
    async def test_concurrent_requests(
        self, mock_stability_config, mock_successful_response
    ):
        service = self.StabilityService(mock_stability_config)

        params_list = [{"prompt": f"Image {i}"} for i in range(3)]

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_successful_response

        with patch.object(service, "_initialize_client"):
            service.client = mock_client

            responses = await asyncio.gather(
                *[service.send_generation_request(params) for params in params_list]
            )

            assert len(responses) == 3
            assert all(response == mock_successful_response for response in responses)

    @pytest.mark.asyncio
    async def test_empty_params_handling(
        self, mock_stability_config, mock_successful_response
    ):
        service = self.StabilityService(mock_stability_config)

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_successful_response

        with patch.object(service, "_initialize_client"):
            service.client = mock_client

            response = await service.send_generation_request({})

            mock_client.post.assert_called_once_with(
                service.host, files={"none": ""}, data={}
            )

            assert response == mock_successful_response

    @pytest.mark.asyncio
    async def test_large_params_handling(
        self, mock_stability_config, mock_successful_response
    ):
        service = self.StabilityService(mock_stability_config)

        large_params = {
            "prompt": "A" * 1000,  # Длинный промпт
            "width": 2048,
            "height": 2048,
        }

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_successful_response

        with patch.object(service, "_initialize_client"):
            service.client = mock_client

            response = await service.send_generation_request(large_params)

            mock_client.post.assert_called_once()
            assert response == mock_successful_response
