import pytest
from fastapi import Request, status
from fastapi.datastructures import Headers
from fastapi.responses import JSONResponse
from mcp_server_qdrant.middleware import PayloadSizeMiddleware


@pytest.fixture
def response_fixture():
    """Fixture to provide a response object for testing."""

    async def inner(_: Request) -> JSONResponse:
        return JSONResponse({"detail": "ok"})

    return inner


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ["max_size", "status_code", "expected_body"],
    [
        (1_000_000, status.HTTP_200_OK, b'{"detail":"ok"}'),
        (
            5,
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            b'{"detail":"Payload too large"}',
        ),
    ],
    ids=["valid", "overlimit"],
)
async def test_payload_size_middleware(
    response_fixture, max_size, status_code, expected_body
):
    """Test the PayloadSizeMiddleware with different max sizes."""

    middleware = PayloadSizeMiddleware(app=response_fixture)
    middleware.max_size = max_size
    headers = Headers({"content-length": "10"})
    request = Request({"type": "http", "headers": headers.raw})
    response = await middleware.dispatch(request, response_fixture)
    assert response.status_code == status_code
    assert response.body == expected_body
