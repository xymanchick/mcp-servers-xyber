import base64
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp_server_stability.server import app_lifespan, mcp_server
from mcp_server_stability.stable_diffusion import (
    StabilityService, StableDiffusionClientError,
    StableDiffusionServerConnectionError)

tools = mcp_server._tool_manager._tools
generate_image_tool = tools.get("generate_image")

if generate_image_tool is None:
    raise RuntimeError("generate_image tool not found in MCP server")

generate_image_func = generate_image_tool.fn


@pytest.fixture
def mock_stability_service():
    service = AsyncMock(spec=StabilityService)
    service.cleanup = AsyncMock()
    return service


@pytest.fixture
def mock_context():
    context = Mock()
    context.request_context = Mock()
    context.request_context.lifespan_context = {}
    return context


@pytest.fixture
def sample_image_data():
    return b"fake_image_data_for_testing"


@pytest.fixture
def sample_base64_image():
    return base64.b64encode(b"fake_image_data_for_testing").decode("utf-8")


class TestAppLifespan:
    @pytest.mark.asyncio
    async def test_app_lifespan_success(self, mock_stability_service):
        mock_server = Mock(spec=FastMCP)

        with patch(
            "mcp_server_stability.server.get_stability_service",
            return_value=mock_stability_service,
        ):
            async with app_lifespan(mock_server) as context:
                assert "stability_service" in context
                assert context["stability_service"] == mock_stability_service

        mock_stability_service.cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_app_lifespan_initialization_error(self):
        mock_server = Mock(spec=FastMCP)
        error_msg = "API key not found"

        with patch(
            "mcp_server_stability.server.get_stability_service",
            side_effect=StableDiffusionClientError(error_msg),
        ):
            with pytest.raises(StableDiffusionClientError, match=error_msg):
                async with app_lifespan(mock_server):
                    pass

    @pytest.mark.asyncio
    async def test_app_lifespan_unexpected_error(self):
        mock_server = Mock(spec=FastMCP)
        error_msg = "Unexpected startup error"

        with patch(
            "mcp_server_stability.server.get_stability_service",
            side_effect=RuntimeError(error_msg),
        ):
            with pytest.raises(RuntimeError, match=error_msg):
                async with app_lifespan(mock_server):
                    pass

    @pytest.mark.asyncio
    async def test_app_lifespan_cleanup_called_on_exception(
        self, mock_stability_service
    ):
        mock_server = Mock(spec=FastMCP)

        with patch(
            "mcp_server_stability.server.get_stability_service",
            return_value=mock_stability_service,
        ):
            try:
                async with app_lifespan(mock_server):
                    raise ValueError("Test exception")
            except ValueError:
                pass

        mock_stability_service.cleanup.assert_called_once()


class TestGenerateImage:
    @pytest.mark.asyncio
    async def test_generate_image_success(
        self,
        mock_context,
        mock_stability_service,
        sample_image_data,
        sample_base64_image,
    ):
        mock_context.request_context.lifespan_context["stability_service"] = (
            mock_stability_service
        )

        mock_response = Mock()
        mock_response.headers = {}
        mock_response.content = sample_image_data
        mock_stability_service.send_generation_request.return_value = mock_response

        result = await generate_image_func(
            ctx=mock_context,
            prompt="A beautiful sunset",
            negative_prompt="ugly, blurry",
            aspect_ratio="16:9",
            seed=123,
            style_preset="photographic",
        )

        assert result == sample_base64_image

        expected_params = {
            "prompt": "A beautiful sunset",
            "negative_prompt": "ugly, blurry",
            "aspect_ratio": "16:9",
            "seed": 123,
            "style_preset": "photographic",
        }
        mock_stability_service.send_generation_request.assert_called_once_with(
            expected_params
        )

    @pytest.mark.asyncio
    async def test_generate_image_with_defaults(
        self,
        mock_context,
        mock_stability_service,
        sample_image_data,
        sample_base64_image,
    ):
        mock_context.request_context.lifespan_context["stability_service"] = (
            mock_stability_service
        )

        mock_response = Mock()
        mock_response.headers = {}
        mock_response.content = sample_image_data
        mock_stability_service.send_generation_request.return_value = mock_response

        result = await generate_image_func(
            ctx=mock_context, prompt="A simple test image"
        )

        assert result == sample_base64_image

        expected_params = {
            "prompt": "A simple test image",
            "negative_prompt": "ugly, inconsistent",
            "aspect_ratio": "1:1",
            "seed": 42,
        }
        mock_stability_service.send_generation_request.assert_called_once_with(
            expected_params
        )

    @pytest.mark.asyncio
    async def test_generate_image_without_style_preset(
        self, mock_context, mock_stability_service, sample_image_data
    ):
        mock_context.request_context.lifespan_context["stability_service"] = (
            mock_stability_service
        )

        mock_response = Mock()
        mock_response.headers = {}
        mock_response.content = sample_image_data
        mock_stability_service.send_generation_request.return_value = mock_response

        await generate_image_func(
            ctx=mock_context, prompt="Test prompt", style_preset=None
        )

        call_args = mock_stability_service.send_generation_request.call_args[0][0]
        assert "style_preset" not in call_args

    @pytest.mark.asyncio
    async def test_generate_image_content_filtered(
        self, mock_context, mock_stability_service
    ):
        mock_context.request_context.lifespan_context["stability_service"] = (
            mock_stability_service
        )

        mock_response = Mock()
        mock_response.headers = {"finish-reason": "CONTENT_FILTERED"}
        mock_response.content = b"dummy_content"
        mock_stability_service.send_generation_request.return_value = mock_response

        with pytest.raises(ToolError, match="Generation failed: NSFW content filtered"):
            await generate_image_func(ctx=mock_context, prompt="Test prompt")

    @pytest.mark.asyncio
    async def test_generate_image_server_connection_error(
        self, mock_context, mock_stability_service
    ):
        mock_context.request_context.lifespan_context["stability_service"] = (
            mock_stability_service
        )

        error_msg = "Connection timeout"
        mock_stability_service.send_generation_request.side_effect = (
            StableDiffusionServerConnectionError(error_msg)
        )

        with pytest.raises(ToolError, match=error_msg):
            await generate_image_func(ctx=mock_context, prompt="Test prompt")

    @pytest.mark.asyncio
    async def test_generate_image_client_error(
        self, mock_context, mock_stability_service
    ):
        mock_context.request_context.lifespan_context["stability_service"] = (
            mock_stability_service
        )

        error_msg = "Invalid API key"
        mock_stability_service.send_generation_request.side_effect = (
            StableDiffusionClientError(error_msg)
        )

        with pytest.raises(ToolError, match=error_msg):
            await generate_image_func(ctx=mock_context, prompt="Test prompt")

    @pytest.mark.asyncio
    async def test_generate_image_unexpected_error(
        self, mock_context, mock_stability_service
    ):
        mock_context.request_context.lifespan_context["stability_service"] = (
            mock_stability_service
        )

        error_msg = "Unexpected network error"
        mock_stability_service.send_generation_request.side_effect = RuntimeError(
            error_msg
        )

        with pytest.raises(ToolError, match=f"Unexpected error: {error_msg}"):
            await generate_image_func(ctx=mock_context, prompt="Test prompt")

    @pytest.mark.asyncio
    async def test_generate_image_different_aspect_ratios(
        self,
        mock_context,
        mock_stability_service,
        sample_image_data,
        sample_base64_image,
    ):
        mock_context.request_context.lifespan_context["stability_service"] = (
            mock_stability_service
        )

        mock_response = Mock()
        mock_response.headers = {}
        mock_response.content = sample_image_data
        mock_stability_service.send_generation_request.return_value = mock_response

        result = await generate_image_func(
            ctx=mock_context, prompt="Test portrait", aspect_ratio="9:16"
        )

        assert result == sample_base64_image
        call_args = mock_stability_service.send_generation_request.call_args[0][0]
        assert call_args["aspect_ratio"] == "9:16"

    @pytest.mark.asyncio
    async def test_generate_image_different_style_presets(
        self,
        mock_context,
        mock_stability_service,
        sample_image_data,
        sample_base64_image,
    ):
        mock_context.request_context.lifespan_context["stability_service"] = (
            mock_stability_service
        )

        mock_response = Mock()
        mock_response.headers = {}
        mock_response.content = sample_image_data
        mock_stability_service.send_generation_request.return_value = mock_response

        result = await generate_image_func(
            ctx=mock_context, prompt="Test anime style", style_preset="anime"
        )

        assert result == sample_base64_image
        call_args = mock_stability_service.send_generation_request.call_args[0][0]
        assert call_args["style_preset"] == "anime"

    @pytest.mark.asyncio
    async def test_generate_image_with_zero_seed(
        self,
        mock_context,
        mock_stability_service,
        sample_image_data,
        sample_base64_image,
    ):
        mock_context.request_context.lifespan_context["stability_service"] = (
            mock_stability_service
        )

        mock_response = Mock()
        mock_response.headers = {}
        mock_response.content = sample_image_data
        mock_stability_service.send_generation_request.return_value = mock_response

        result = await generate_image_func(
            ctx=mock_context, prompt="Random test image", seed=0
        )

        assert result == sample_base64_image
        call_args = mock_stability_service.send_generation_request.call_args[0][0]
        assert call_args["seed"] == 0


class TestMCPServer:
    def test_mcp_server_creation(self):
        assert mcp_server.name == "stability-server"

    @pytest.mark.asyncio
    async def test_generate_image_missing_stability_service(self, mock_context):
        mock_context.request_context.lifespan_context = {}

        with pytest.raises(KeyError):
            await generate_image_func(ctx=mock_context, prompt="Test prompt")
