import os
from collections.abc import AsyncGenerator
from pathlib import Path

import httpx
import pytest
import pytest_asyncio
from dotenv import load_dotenv

# Load .env.tests file if it exists
env_tests_path = Path(__file__).parent.parent / ".env.tests"
if env_tests_path.exists():
    load_dotenv(env_tests_path)


@pytest.fixture(scope="session")
def server_url() -> str:
    """Get URL of already-running server from environment.

    User must start the server manually before running e2e tests:
        uv run uvicorn mcp_server_qdrant.app:create_app --factory --port 8000

    Set E2E_SERVER_URL in environment or .env.tests file.
    """
    url = os.getenv("E2E_SERVER_URL", "http://localhost:8000")
    return url.rstrip("/")


@pytest_asyncio.fixture
async def http_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """Async HTTP client for e2e tests."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        yield client
