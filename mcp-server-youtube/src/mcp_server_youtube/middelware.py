from fastapi import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class PayloadSizeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        max_size = 1_000_000  # 1MB
        content_length = int(request.headers.get("content-length", 0))
        if content_length > max_size:
            raise HTTPException(status_code=413, detail="Payload too large")
        return await call_next(request)