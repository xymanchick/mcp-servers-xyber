from fastapi import requests, responses, status
from starlette.middleware.base import BaseHTTPMiddleware


class PayloadSizeMiddleware(BaseHTTPMiddleware):
    max_size: int = 1_000_000  # 1 MB default limit

    async def dispatch(self, request: requests.Request, call_next):
        content_length = int(request.headers.get("content-length", 0))

        if content_length > self.max_size:
            return responses.JSONResponse(
                content=dict(detail="Payload too large"),
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            )

        return await call_next(request)
