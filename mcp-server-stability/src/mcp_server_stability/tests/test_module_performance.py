import pytest
from unittest.mock import AsyncMock, Mock, patch
import asyncio
import time


def get_stability_module():
    try:
        from mcp_server_stability.stable_diffusion.module import StabilityService, get_stability_service
        from mcp_server_stability.stable_diffusion.config import (
            StableDiffusionClientError,
            StableDiffusionServerConnectionError,
        )
        return StabilityService, get_stability_service, StableDiffusionClientError, StableDiffusionServerConnectionError
    except ImportError as e:
        pytest.skip(f"Failed to import module: {e}")


class TestStabilityServicePerformance:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.StabilityService, self.get_stability_service, self.ClientError, self.ConnectionError = get_stability_module()

    @pytest.mark.asyncio
    async def test_single_request_performance(self, mock_stability_config, sample_generation_params, mock_successful_response):
        """Тест производительности одиночного запроса"""
        service = self.StabilityService(mock_stability_config)
        
        # Настройка мока с имитацией реального времени ответа
        mock_client = AsyncMock()
        
        async def mock_post(*args, **kwargs):
            # Имитация времени обработки API (10ms)
            await asyncio.sleep(0.01)
            return mock_successful_response
            
        mock_client.post = mock_post
        
        with patch('httpx.AsyncClient', return_value=mock_client):
            start_time = time.time()
            response = await service.send_generation_request(sample_generation_params)
            end_time = time.time()
            
            execution_time = end_time - start_time
            
            assert execution_time < 0.1
            assert response == mock_successful_response
            
            await service.cleanup()

    @pytest.mark.asyncio
    async def test_concurrent_requests_performance(self, mock_stability_config, mock_successful_response):
        """Тест производительности конкурентных запросов"""
        service = self.StabilityService(mock_stability_config)
        
        concurrent_requests = 10
        
        mock_client = AsyncMock()
        
        async def mock_post(*args, **kwargs):
            await asyncio.sleep(0.01)
            return mock_successful_response
            
        mock_client.post = mock_post
        
        params_list = [
            {"prompt": f"Performance test {i}", "width": 512, "height": 512}
            for i in range(concurrent_requests)
        ]
        
        with patch('httpx.AsyncClient', return_value=mock_client):
            start_time = time.time()
            
            responses = await asyncio.gather(*[
                service.send_generation_request(params) for params in params_list
            ])
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            # Конкурентные запросы должны выполняться быстрее последовательных
            # При 10 запросах по 10ms каждый, конкурентное выполнение должно быть ~10ms
            assert execution_time < 0.05  # 50ms максимум
            assert len(responses) == concurrent_requests
            assert all(response == mock_successful_response for response in responses)
            
            await service.cleanup()

    @pytest.mark.asyncio
    async def test_memory_usage_with_multiple_requests(self, mock_stability_config, mock_successful_response):
        service = self.StabilityService(mock_stability_config)
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_successful_response
        
        with patch('httpx.AsyncClient', return_value=mock_client):
            for i in range(50):
                params = {"prompt": f"Memory test {i}"}
                response = await service.send_generation_request(params)
                assert response == mock_successful_response
            
            assert service.client is not None
            
            await service.cleanup()
            assert service.client is None

    @pytest.mark.asyncio
    async def test_client_reuse_efficiency(self, mock_stability_config, mock_successful_response):
        service = self.StabilityService(mock_stability_config)
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_successful_response
        
        creation_count = 0
        
        def count_client_creation(*args, **kwargs):
            nonlocal creation_count
            creation_count += 1
            return mock_client
        
        with patch('httpx.AsyncClient', side_effect=count_client_creation):
            for i in range(5):
                params = {"prompt": f"Reuse test {i}"}
                await service.send_generation_request(params)
            
            assert creation_count == 1
            
            await service.cleanup()


class TestStabilityServiceLoadTesting:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.StabilityService, self.get_stability_service, self.ClientError, self.ConnectionError = get_stability_module()

    @pytest.mark.asyncio
    async def test_high_concurrency_load(self, mock_stability_config, mock_successful_response):
        service = self.StabilityService(mock_stability_config)
        
        high_load_count = 100
        
        mock_client = AsyncMock()
        
        async def mock_post(*args, **kwargs):
            await asyncio.sleep(0.001)
            return mock_successful_response
            
        mock_client.post = mock_post
        
        params_list = [
            {"prompt": f"Load test {i}"} for i in range(high_load_count)
        ]
        
        with patch('httpx.AsyncClient', return_value=mock_client):
            start_time = time.time()
            
            responses = await asyncio.gather(*[
                service.send_generation_request(params) for params in params_list
            ])
            
            end_time = time.time()
            
            assert len(responses) == high_load_count
            assert all(response == mock_successful_response for response in responses)
            
            assert (end_time - start_time) < 1.0
            
            await service.cleanup()

    @pytest.mark.asyncio
    async def test_stress_with_errors(self, mock_stability_config):
        service = self.StabilityService(mock_stability_config)
        
        mock_client = AsyncMock()
        
        # Имитируем случайные ошибки (30% запросов)
        call_count = 0
        async def mock_post_with_errors(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            
            if call_count % 3 == 0:  # Каждый третий запрос - ошибка
                raise Exception("Simulated API error")
            else:
                mock_response = Mock()
                mock_response.is_success = True
                return mock_response
        
        mock_client.post = mock_post_with_errors
        
        params_list = [{"prompt": f"Stress test {i}"} for i in range(30)]
        
        with patch('httpx.AsyncClient', return_value=mock_client):
            successful_responses = 0
            failed_requests = 0
            
            # Выполняем запросы с обработкой ошибок
            for params in params_list:
                try:
                    response = await service.send_generation_request(params)
                    if response.is_success:
                        successful_responses += 1
                except self.ClientError:
                    failed_requests += 1
                    # После ошибки клиент должен сброситься
                    service.client = None
            
            # Проверяем что примерно 70% запросов успешны, 30% с ошибками
            assert successful_responses >= 15  # Минимум 50% успешных
            assert failed_requests >= 5       # Минимум 5 ошибок
            
            await service.cleanup()

    @pytest.mark.asyncio
    async def test_long_running_service(self, mock_stability_config, mock_successful_response):
        """Тест длительной работы сервиса"""
        service = self.StabilityService(mock_stability_config)
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_successful_response
        
        with patch('httpx.AsyncClient', return_value=mock_client):
            # Имитируем длительную работу с периодическими запросами
            total_requests = 0
            
            for batch in range(5):  # 5 батчей
                # Запросы в батче
                batch_requests = []
                for i in range(10):  # 10 запросов на батч
                    params = {"prompt": f"Long running batch {batch} request {i}"}
                    batch_requests.append(service.send_generation_request(params))
                
                # Выполняем батч
                responses = await asyncio.gather(*batch_requests)
                total_requests += len(responses)
                
                # Проверяем что все запросы в батче успешны
                assert all(response == mock_successful_response for response in responses)
                
                # Небольшая пауза между батчами
                await asyncio.sleep(0.01)
            
            # Проверяем общее количество обработанных запросов
            assert total_requests == 50
            assert mock_client.post.call_count == 50
            
            await service.cleanup()

    @pytest.mark.asyncio
    async def test_resource_cleanup_under_load(self, mock_stability_config, mock_successful_response):
        """Тест очистки ресурсов под нагрузкой"""
        services = []
        
        # Создаем несколько сервисов
        for i in range(10):
            service = self.StabilityService(mock_stability_config)
            services.append(service)
        
        mock_clients = []
        for i in range(10):
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_successful_response
            mock_clients.append(mock_client)
        
        with patch('httpx.AsyncClient', side_effect=mock_clients):
            # Запускаем запросы во всех сервисах одновременно
            all_requests = []
            for i, service in enumerate(services):
                params = {"prompt": f"Multi-service request {i}"}
                all_requests.append(service.send_generation_request(params))
            
            responses = await asyncio.gather(*all_requests)
            assert len(responses) == 10
            
            cleanup_tasks = [service.cleanup() for service in services]
            await asyncio.gather(*cleanup_tasks)
            
            for mock_client in mock_clients:
                mock_client.aclose.assert_called_once()
            
            for service in services:
                assert service.client is None
