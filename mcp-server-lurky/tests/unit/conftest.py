import pytest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from mcp_server_lurky.app import create_app


@pytest.fixture
def app() -> FastAPI:
    """Create FastAPI app for testing with x402 disabled."""
    with patch('mcp_server_lurky.app.get_x402_settings') as mock_x402:
        mock_x402.return_value.pricing_mode = "off"
        return create_app()


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create test client."""
    return TestClient(app)
