import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
from contextlib import asynccontextmanager

sys.modules["mcp_server_imgen.google_client"] = MagicMock()
sys.modules["mcp_server_imgen.utils"] = MagicMock()
sys.modules["fastmcp"] = MagicMock()
sys.modules["fastmcp.exceptions"] = MagicMock()

@pytest.fixture
def mock_google_service():
    return MagicMock()

@pytest.fixture
def mock_image_generator():
    mock_generator = AsyncMock()
    mock_generator.generate_images = AsyncMock(return_value=["base64_image_data"])
    return mock_generator

@pytest.fixture
def mock_context(mock_image_generator):
    mock_context = MagicMock()
    mock_context.request_context.lifespan_context = {"image_generator": mock_image_generator}
    return mock_context

@pytest.fixture
def mock_context_with_custom_generator():
    def _create_context(image_generator):
        mock_context = MagicMock()
        mock_context.request_context.lifespan_context = {"image_generator": image_generator}
        return mock_context
    return _create_context

@pytest.fixture
def mock_server_patches():
    with patch('mcp_server_imgen.server.get_google_service') as mock_get_google, \
         patch('mcp_server_imgen.server.get_image_generation_service') as mock_get_image_gen:
        yield {
            'google_service': mock_get_google,
            'image_generation_service': mock_get_image_gen
        }

@pytest.fixture
def mock_generate_image_function():
    async def mock_generate_image(ctx, prompt, width=512, height=512, num_images=1, seed=None, guidance_scale=7.5, num_inference_steps=50):
        image_generator = ctx.request_context.lifespan_context["image_generator"]
        image_base64_list = await image_generator.generate_images(
            prompt=prompt,
            width=width,
            height=height,
            num_images=num_images,
            seed=seed,
            guidance_scale=guidance_scale,
            num_inference_steps=num_inference_steps,
        )
        return image_base64_list[0]
    return mock_generate_image

@pytest.fixture
def tool_error_class():
    try:
        from fastmcp.exceptions import ToolError
        return ToolError
    except ImportError:
        class ToolError(Exception):
            pass
        return ToolError

@pytest.fixture
def test_app(mock_google_service, mock_image_generator):
    from fastapi import FastAPI
    
    app = FastAPI(
        title="Image Generation MCP Server",
        description="MCP server for generating images using Google Vertex AI",
        version="1.0.0"
    )
    
    @app.get("/mcp-server/mcp")
    @app.post("/mcp-server/mcp")  
    @app.options("/mcp-server/mcp")
    def mock_mcp_endpoint():
        return {"status": "ok"}
    
    return app