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


class TestStabilityServiceIntegration:
    @pytest.fixture(autouse=True)
    def setup(self):
        (
            self.StabilityService,
            self.get_stability_service,
            self.ClientError,
            self.ConnectionError,
        ) = get_stability_module()

    @pytest.mark.asyncio
    async def test_full_service_lifecycle(
        self, mock_stability_config, sample_generation_params, mock_successful_response
    ):
        service = self.StabilityService(mock_stability_config)

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_successful_response

        with patch("httpx.AsyncClient") as mock_httpx:
            mock_httpx.return_value = mock_client

            # 1. Отправка запроса (должна инициализировать клиента)
            response = await service.send_generation_request(sample_generation_params)

            assert response == mock_successful_response
            assert service.client is not None

            await service.cleanup()
            assert service.client is None

            mock_client.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_service_factory_and_usage(
        self, sample_generation_params, mock_successful_response
    ):
        mock_config = Mock()
        mock_config.api_key = "factory-test-key"
        mock_config.host = "https://factory-test.api"

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_successful_response

        with patch(
            "mcp_server_stability.stable_diffusion.module.StableDiffusionClientConfig"
        ) as mock_config_class:
            mock_config_class.return_value = mock_config

            with patch("httpx.AsyncClient", return_value=mock_client):
                service = await self.get_stability_service()

                response = await service.send_generation_request(
                    sample_generation_params
                )

                await service.cleanup()

                assert isinstance(service, self.StabilityService)
                assert response == mock_successful_response
                mock_client.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_error_recovery_scenario(
        self, mock_stability_config, sample_generation_params
    ):
        service = self.StabilityService(mock_stability_config)

        # Первый клиент с ошибкой
        failing_client = AsyncMock()
        failing_client.post.side_effect = Exception("Connection lost")

        # Второй клиент успешный
        success_client = AsyncMock()
        mock_success_response = Mock()
        mock_success_response.is_success = True
        success_client.post.return_value = mock_success_response

        with patch("httpx.AsyncClient", side_effect=[failing_client, success_client]):
            # Первый запрос должен завершиться ошибкой
            with pytest.raises(self.ClientError):
                await service.send_generation_request(sample_generation_params)

            # Клиент должен остаться None после ошибки
            assert service.client is None

            # Второй запрос должен быть успешным
            response = await service.send_generation_request(sample_generation_params)
            assert response == mock_success_response

    @pytest.mark.asyncio
    async def test_multiple_services_isolation(
        self, sample_generation_params, mock_successful_response
    ):
        config1 = Mock()
        config1.api_key = "service1-key"
        config1.host = "https://service1.api"

        config2 = Mock()
        config2.api_key = "service2-key"
        config2.host = "https://service2.api"

        service1 = self.StabilityService(config1)
        service2 = self.StabilityService(config2)

        mock_client1 = AsyncMock()
        mock_client1.post.return_value = mock_successful_response

        mock_client2 = AsyncMock()
        mock_client2.post.return_value = mock_successful_response

        with patch("httpx.AsyncClient", side_effect=[mock_client1, mock_client2]):
            # Выполняем запросы в разных сервисах
            response1 = await service1.send_generation_request(sample_generation_params)
            response2 = await service2.send_generation_request(sample_generation_params)

            # Проверяем что запросы выполнились с правильными хостами
            mock_client1.post.assert_called_once_with(
                config1.host, files={"none": ""}, data=sample_generation_params
            )

            mock_client2.post.assert_called_once_with(
                config2.host, files={"none": ""}, data=sample_generation_params
            )

            await service1.cleanup()
            await service2.cleanup()

            mock_client1.aclose.assert_called_once()
            mock_client2.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_concurrent_service_operations(
        self, mock_stability_config, mock_successful_response
    ):
        service = self.StabilityService(mock_stability_config)

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_successful_response

        params_sets = [
            {"prompt": "Sunset landscape", "width": 512, "height": 512},
            {"prompt": "City skyline", "width": 768, "height": 768},
            {"prompt": "Abstract art", "width": 1024, "height": 1024},
        ]

        with patch("httpx.AsyncClient", return_value=mock_client):
            responses = await asyncio.gather(
                *[service.send_generation_request(params) for params in params_sets]
            )

            assert len(responses) == 3
            assert all(response == mock_successful_response for response in responses)

            assert mock_client.post.call_count == 3

            await service.cleanup()


class TestStabilityServiceWorkflowIntegration:
    @pytest.fixture(autouse=True)
    def setup(self):
        (
            self.StabilityService,
            self.get_stability_service,
            self.ClientError,
            self.ConnectionError,
        ) = get_stability_module()

    @pytest.mark.asyncio
    async def test_request_retry_workflow(
        self, mock_stability_config, sample_generation_params
    ):
        service = self.StabilityService(mock_stability_config)

        # Первый запрос неудачный, второй успешный
        mock_client = AsyncMock()

        call_count = 0

        async def mock_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # Первый вызов - ошибка
                raise Exception("Temporary failure")
            else:
                # Второй вызов - успех
                mock_response = Mock()
                mock_response.is_success = True
                return mock_response

        mock_client.post = mock_post

        with patch("httpx.AsyncClient", return_value=mock_client):
            # Первый запрос завершится ошибкой
            with pytest.raises(self.ClientError):
                await service.send_generation_request(sample_generation_params)

            # Клиент остается None после ошибки инициализации
            service.client = None

            # Второй запрос должен быть успешным (новый клиент)
            with patch("httpx.AsyncClient", return_value=mock_client):
                mock_client.post = AsyncMock(return_value=Mock(is_success=True))
                response = await service.send_generation_request(
                    sample_generation_params
                )
                assert response.is_success

    @pytest.mark.asyncio
    async def test_batch_processing_workflow(
        self, mock_stability_config, mock_successful_response
    ):
        service = self.StabilityService(mock_stability_config)

        batch_requests = [
            {"prompt": f"Image batch {i}", "width": 512, "height": 512}
            for i in range(5)
        ]

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_successful_response

        with patch("httpx.AsyncClient", return_value=mock_client):
            results = []
            for params in batch_requests:
                response = await service.send_generation_request(params)
                results.append(response)

            assert len(results) == 5
            assert all(result == mock_successful_response for result in results)
            assert mock_client.post.call_count == 5

            await service.cleanup()

    @pytest.mark.asyncio
    async def test_configuration_change_workflow(
        self, sample_generation_params, mock_successful_response
    ):
        config1 = Mock()
        config1.api_key = "initial-key"
        config1.host = "https://initial.api"

        service = self.StabilityService(config1)

        mock_client1 = AsyncMock()
        mock_client1.post.return_value = mock_successful_response

        with patch("httpx.AsyncClient", return_value=mock_client1):
            # Первый запрос с исходной конфигурацией
            response1 = await service.send_generation_request(sample_generation_params)
            assert response1 == mock_successful_response

            # Проверяем что запрос отправлен на правильный host
            mock_client1.post.assert_called_with(
                config1.host, files={"none": ""}, data=sample_generation_params
            )

            await service.cleanup()

            config2 = Mock()
            config2.api_key = "updated-key"
            config2.host = "https://updated.api"

            service2 = self.StabilityService(config2)

            mock_client2 = AsyncMock()
            mock_client2.post.return_value = mock_successful_response

            with patch("httpx.AsyncClient", return_value=mock_client2):
                response2 = await service2.send_generation_request(
                    sample_generation_params
                )
                assert response2 == mock_successful_response

                mock_client2.post.assert_called_with(
                    config2.host, files={"none": ""}, data=sample_generation_params
                )

                await service2.cleanup()
