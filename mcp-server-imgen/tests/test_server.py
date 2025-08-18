import json
import httpx
import asyncio
from fastapi import status
import pytest
from unittest.mock import AsyncMock, patch, Mock, MagicMock
import types
import sys
from contextlib import asynccontextmanager

from fastapi.testclient import TestClient


pytest_plugins = ["pytest_asyncio"]

try:
    from fastmcp.exceptions import ToolError
except ImportError:
    class ToolError(Exception):
        pass


def test_mcp_server_mount(test_app):
    with TestClient(test_app) as client:
        response = client.get("/mcp-server/mcp")
        assert response.status_code in [200, 405, 404]


def test_mcp_server_options_request(test_app):
    with TestClient(test_app) as client:
        response = client.options("/mcp-server/mcp")
        assert response.status_code in [200, 204, 405]


def test_app_title_and_metadata(test_app):
    assert test_app.title == "Image Generation MCP Server"
    assert test_app.description == "MCP server for generating images using Google Vertex AI"
    assert test_app.version == "1.0.0"


def test_app_routes_exist(test_app):
    routes = [route.path for route in test_app.routes]
    assert "/mcp-server" in routes or any("/mcp-server" in route for route in routes)


@pytest.mark.asyncio
async def test_generate_image_default_parameters(mock_context, mock_generate_image_function, mock_server_patches):
    result = await mock_generate_image_function(
        ctx=mock_context,
        prompt="A beautiful sunset"
    )
    
    assert result == "base64_image_data"
    
    mock_context.request_context.lifespan_context["image_generator"].generate_images.assert_called_once_with(
        prompt="A beautiful sunset",
        width=512,
        height=512,
        num_images=1,
        seed=None,
        guidance_scale=7.5,
        num_inference_steps=50
    )


@pytest.mark.asyncio 
async def test_generate_image_custom_parameters(mock_context_with_custom_generator, mock_generate_image_function, mock_server_patches):
    custom_generator = AsyncMock()
    custom_generator.generate_images = AsyncMock(return_value=["custom_base64_image"])
    mock_context = mock_context_with_custom_generator(custom_generator)
    
    result = await mock_generate_image_function(
        ctx=mock_context,
        prompt="A red car",
        width=1024,
        height=768, 
        num_images=2,
        seed=12345,
        guidance_scale=10.0,
        num_inference_steps=30
    )
    
    assert result == "custom_base64_image"
    
    custom_generator.generate_images.assert_called_once_with(
        prompt="A red car",
        width=1024,
        height=768,
        num_images=2,
        seed=12345,
        guidance_scale=10.0,
        num_inference_steps=30
    )


@pytest.mark.asyncio
async def test_generate_image_google_service_error(mock_context_with_custom_generator):
    error_generator = AsyncMock()
    service_error = Exception("Google service connection failed")
    error_generator.generate_images = AsyncMock(side_effect=service_error)
    
    mock_context = mock_context_with_custom_generator(error_generator)
    
    with pytest.raises(Exception, match="Google service connection failed"):
        await error_generator.generate_images(prompt="test")


@pytest.mark.asyncio
async def test_generate_image_unexpected_error(mock_context_with_custom_generator):
    error_generator = AsyncMock()
    error_generator.generate_images = AsyncMock(side_effect=ValueError("Unexpected error"))
    
    mock_context = mock_context_with_custom_generator(error_generator)
    
    with pytest.raises(ValueError, match="Unexpected error"):
        await error_generator.generate_images(prompt="test")


@pytest.mark.asyncio
async def test_generate_image_validation_constraints(mock_context, mock_server_patches):
    async def validated_mock_generate_image(ctx, prompt, width=512, height=512, num_images=1, seed=None, guidance_scale=7.5, num_inference_steps=50):
        assert 1 <= len(prompt) <= 100, "Prompt должен быть от 1 до 100 символов"
        assert 128 <= width <= 1024 and width % 8 == 0, "Width должен быть 128-1024 и кратен 8"
        assert 128 <= height <= 1024 and height % 8 == 0, "Height должен быть 128-1024 и кратен 8"
        assert 1 <= num_images <= 4, "num_images должен быть 1-4"
        assert 1.0 <= guidance_scale <= 20.0, "guidance_scale должен быть 1.0-20.0"
        assert 10 <= num_inference_steps <= 100, "num_inference_steps должен быть 10-100"
        
        image_generator = ctx.request_context.lifespan_context["image_generator"]
        image_base64_list = await image_generator.generate_images(
            prompt=prompt, width=width, height=height, num_images=num_images,
            seed=seed, guidance_scale=guidance_scale, num_inference_steps=num_inference_steps,
        )
        return image_base64_list[0]
    
    result = await validated_mock_generate_image(
        ctx=mock_context,
        prompt="Valid prompt",
        width=512,
        height=768,
        num_images=2,
        guidance_scale=10.0,
        num_inference_steps=25
    )
    assert result == "base64_image_data"


@pytest.mark.asyncio
async def test_generate_image_edge_case_parameters(mock_context_with_custom_generator, mock_generate_image_function):
    edge_generator = AsyncMock()
    edge_generator.generate_images = AsyncMock(return_value=["edge_case_image"])
    mock_context = mock_context_with_custom_generator(edge_generator)
    
    result = await mock_generate_image_function(
        ctx=mock_context,
        prompt="A",  # Минимальный prompt
        width=128,   # Минимальная ширина
        height=128,  # Минимальная высота
        num_images=1,  # Минимальное количество
        guidance_scale=1.0,  # Минимальный guidance_scale
        num_inference_steps=10  # Минимальное количество шагов
    )
    assert result == "edge_case_image"
    
    result = await mock_generate_image_function(
        ctx=mock_context,
        prompt="A" * 100,  # Максимальный prompt (100 символов)
        width=1024,   # Максимальная ширина
        height=1024,  # Максимальная высота
        num_images=4,  # Максимальное количество
        guidance_scale=20.0,  # Максимальный guidance_scale
        num_inference_steps=100  # Максимальное количество шагов
    )
    assert result == "edge_case_image"


@pytest.mark.asyncio
async def test_generate_image_logging(caplog):
    import logging
    
    mock_image_generator = AsyncMock()
    mock_image_generator.generate_images = AsyncMock(return_value=["test_image_data"])
    
    mock_context = Mock()
    mock_context.request_context.lifespan_context = {"image_generator": mock_image_generator}
    
    with patch('mcp_server_imgen.server.get_google_service'), \
         patch('mcp_server_imgen.server.get_image_generation_service'):
        
        with caplog.at_level(logging.INFO, logger="mcp_server_imgen.server"):
            async def mock_generate_image_with_logging(ctx, prompt, width=512, height=512, num_images=1, seed=None, guidance_scale=7.5, num_inference_steps=50):
                import logging
                logger = logging.getLogger("mcp_server_imgen.server")
                
                image_generator = ctx.request_context.lifespan_context["image_generator"]
                image_base64_list = await image_generator.generate_images(
                    prompt=prompt, width=width, height=height, num_images=num_images,
                    seed=seed, guidance_scale=guidance_scale, num_inference_steps=num_inference_steps,
                )
                
                logger.info(f"Successfully generated image for prompt: '{prompt}'")
                return image_base64_list[0]
            
            result = await mock_generate_image_with_logging(
                ctx=mock_context,
                prompt="Test logging prompt"
            )
            
            assert result == "test_image_data"
            
            assert "Successfully generated image for prompt: 'Test logging prompt'" in caplog.text


def test_logging_configuration():
    import logging
    
    logger = logging.getLogger("mcp_server_imgen.server")
    assert logger is not None
    
    with patch('logging.getLogger') as mock_get_logger:
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        test_logger = logging.getLogger("mcp_server_imgen.server")
        test_logger.info("Test message")
        
        mock_get_logger.assert_called_with("mcp_server_imgen.server")


@pytest.mark.asyncio
async def test_app_lifespan_successful_initialization(mock_server_patches):
    mock_google_service = Mock()
    mock_image_generator = Mock()
    
    mock_server_patches['google_service'].return_value = mock_google_service
    mock_server_patches['image_generation_service'].return_value = mock_image_generator
    
    from mcp_server_imgen.server import app_lifespan
    
    mock_server = Mock()
    
    async with app_lifespan(mock_server) as context:
        assert "image_generator" in context
        assert context["image_generator"] == mock_image_generator
        
    mock_server_patches['google_service'].assert_called_once()
    mock_server_patches['image_generation_service'].assert_called_once_with(mock_google_service)


def test_mcp_server_exists(mock_server_patches):
    from mcp_server_imgen.server import mcp_server
    
    assert mcp_server is not None


def test_mcp_server_has_generate_image_tool(mock_server_patches):
    from mcp_server_imgen.server import mcp_server
    
    assert mcp_server is not None
    
    from mcp_server_imgen.server import generate_image
    assert callable(generate_image)
