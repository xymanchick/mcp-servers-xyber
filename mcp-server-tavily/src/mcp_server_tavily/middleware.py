from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

import time
import logging
import asyncio

from starlette.responses import Response

logger = logging.getLogger(__name__)

total_requests:int = 0
error_count: int = 0
total_requests_lock = asyncio.Lock()

class ProcessTimeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.perf_counter()
        exception_occured: bool = False
        response = None
        try:
            response = await call_next(request)
        except Exception as e:
            exception_occured = True
            raise e 
        finally:
            if response and (response.status_code<200 or response.status_code >399 ):
                exception_occured = True
            async with total_requests_lock:
                global total_requests
                global error_count
                if exception_occured:
                    error_count+=1
                total_requests +=1
                request_latency_seconds = time.perf_counter() - start_time
                logger.info(f"Request #{total_requests} process time: {request_latency_seconds}; Error: {exception_occured}; { "error_count: "+str(error_count) if exception_occured  else "" }")
        if response:
            return response
