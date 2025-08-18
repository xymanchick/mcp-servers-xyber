import pytest
from fastapi import Request, status
from fastapi.datastructures import Headers
from fastapi.responses import JSONResponse
from mcp_server_qdrant.middleware import PayloadSizeMiddleware


@pytest.mark.asyncio
@pytest.mark.parametrize(
        ["max_size", "status_code", "expected_body"],
        [
            (1_000_000, status.HTTP_200_OK, b'{"detail":"ok"}'),
            (5, status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, b'{"detail":"Payload too large"}'),
        ],
        ids=["valid", "overlimit"]
    )
async def test_payload_size_middleware(response_fixture, max_size, status_code, expected_body):
    middleware = PayloadSizeMiddleware(app=response_fixture)
    middleware.max_size = max_size
    headers = Headers({"content-length": "10"})
    request = Request({"type": "http", "headers": headers.raw})
    response = await middleware.dispatch(request, response_fixture)
    assert response.status_code == status_code
    assert response.body == expected_body


@pytest.mark.asyncio
async def test_payload_size_middleware_no_content_length(response_fixture):
    middleware = PayloadSizeMiddleware(app=response_fixture)
    headers = Headers({})  # No content-length header
    request = Request({"type": "http", "headers": headers.raw})
    response = await middleware.dispatch(request, response_fixture)
    
    assert response.status_code == status.HTTP_200_OK
    assert response.body == b'{"detail":"ok"}'


@pytest.mark.asyncio
async def test_payload_size_middleware_default_max_size(response_fixture):    
    middleware = PayloadSizeMiddleware(app=response_fixture)
    
    headers = Headers({"content-length": "999999"})
    request = Request({"type": "http", "headers": headers.raw})
    response = await middleware.dispatch(request, response_fixture)
    assert response.status_code == status.HTTP_200_OK
    
    headers = Headers({"content-length": "1000001"})
    request = Request({"type": "http", "headers": headers.raw})
    response = await middleware.dispatch(request, response_fixture)
    assert response.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE


@pytest.mark.asyncio
async def test_payload_size_middleware_boundary_case(response_fixture):    
    middleware = PayloadSizeMiddleware(app=response_fixture)
    middleware.max_size = 100
    
    headers = Headers({"content-length": "100"})
    request = Request({"type": "http", "headers": headers.raw})
    response = await middleware.dispatch(request, response_fixture)
    assert response.status_code == status.HTTP_200_OK
    assert response.body == b'{"detail":"ok"}'
    
    headers = Headers({"content-length": "101"})
    request = Request({"type": "http", "headers": headers.raw})
    response = await middleware.dispatch(request, response_fixture)
    assert response.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    assert response.body == b'{"detail":"Payload too large"}'


@pytest.mark.asyncio
async def test_payload_size_middleware_invalid_content_length(response_fixture):    
    middleware = PayloadSizeMiddleware(app=response_fixture)
    
    headers = Headers({"content-length": "invalid"})
    request = Request({"type": "http", "headers": headers.raw})
    
    response = await middleware.dispatch(request, response_fixture)
    
    assert response.status_code == status.HTTP_200_OK
    assert response.body == b'{"detail":"ok"}'
