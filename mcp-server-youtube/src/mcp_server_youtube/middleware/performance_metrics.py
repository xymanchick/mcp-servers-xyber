"""
Performance metrics middleware for YouTube MCP server using Prometheus.

This module provides comprehensive request-level performance monitoring including:
- Request duration tracking using time.perf_counter()
- Request counting by path and method
- Error classification and counting
- Per-request tracing with correlation IDs
- Integration with structured logging
"""

import logging
import time
import uuid
from typing import Dict, Any, Optional
from urllib.parse import urlparse

from fastapi import Request, Response
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse

logger = logging.getLogger(__name__)

# Prometheus Metrics - Fully scoped with youtube_mcp prefix
youtube_mcp_request_count = Counter(
    'youtube_mcp_request_count',
    'Total number of HTTP requests',
    ['method', 'path', 'status_code']
)

youtube_mcp_request_latency_seconds = Histogram(
    'youtube_mcp_request_latency_seconds',
    'Request latency in seconds',
    ['method', 'path'],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

youtube_mcp_error_count = Counter(
    'youtube_mcp_error_count',
    'Total number of errors by type',
    ['method', 'path', 'error_type']
)

youtube_mcp_error_count_total = Counter(
    'youtube_mcp_error_count_total',
    'Total number of errors across all types',
    ['method', 'path']
)


class PerformanceMetricsMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for comprehensive request-level performance monitoring.
    
    Features:
    - Request duration tracking with time.perf_counter()
    - Error classification (validation_error, youtube_api_error, internal_error)
    - Per-request tracing with request ID and user agent
    - Prometheus metrics integration
    - Correlated structured logging
    """

    def __init__(self, app, include_query_params: bool = True):
        super().__init__(app)
        self.include_query_params = include_query_params
        logger.info("Performance metrics middleware initialized")

    async def dispatch(self, request: Request, call_next) -> Response:
        # Generate request ID for tracing
        request_id = str(uuid.uuid4())
        user_agent = request.headers.get('user-agent', 'unknown')
        
        # Store tracing context in request.state
        request.state.request_id = request_id
        request.state.user_agent = user_agent
        request.state.start_time = time.perf_counter()
        
        # Extract request information
        method = request.method
        path = self._normalize_path(request.url.path)
        query_params = dict(request.query_params) if self.include_query_params else {}
        
        # Log request start with correlation info
        logger.info(
            f"Request started",
            extra={
                'request_id': request_id,
                'method': method,
                'path': path,
                'user_agent': user_agent,
                'client_ip': self._get_client_ip(request),
                'query_params': self._sanitize_query_params(query_params)
            }
        )

        response = None
        error_type = None
        
        try:
            # Process the request
            response = await call_next(request)
            status_code = response.status_code
            
            # Determine if this is an error response
            if status_code >= 400:
                error_type = self._classify_error_by_status(status_code)
                
        except Exception as e:
            # Handle uncaught exceptions
            status_code = 500
            error_type = self._classify_error_by_exception(e)
            
            logger.error(
                f"Uncaught exception in request processing",
                extra={
                    'request_id': request_id,
                    'method': method,
                    'path': path,
                    'error_type': error_type,
                    'exception_type': type(e).__name__,
                    'exception_message': str(e)
                },
                exc_info=True
            )
            
            # Create error response
            response = StarletteResponse(
                content='{"error": "Internal server error", "code": "INTERNAL_ERROR"}',
                status_code=500,
                media_type="application/json"
            )
            
        finally:
            # Calculate request duration
            duration = time.perf_counter() - request.state.start_time
            
            # Update Prometheus metrics
            self._update_metrics(method, path, status_code, duration, error_type)
            
            # Log request completion with correlation info
            log_level = logging.ERROR if status_code >= 500 else logging.WARNING if status_code >= 400 else logging.INFO
            logger.log(
                log_level,
                f"Request completed",
                extra={
                    'request_id': request_id,
                    'method': method,
                    'path': path,
                    'status_code': status_code,
                    'duration_seconds': round(duration, 4),
                    'error_type': error_type,
                    'user_agent': user_agent,
                    'response_size': getattr(response, 'headers', {}).get('content-length', 'unknown')
                }
            )

        return response

    def _normalize_path(self, path: str) -> str:
        """Normalize path for consistent metrics labeling."""
        # Remove query parameters and normalize common paths
        if path.startswith('/youtube_search_and_transcript'):
            return '/youtube_search_and_transcript'
        elif path.startswith('/sse'):
            return '/sse'
        elif path.startswith('/metrics'):
            return '/metrics'
        elif path.startswith('/health'):
            return '/health'
        elif path.startswith('/docs'):
            return '/docs'
        elif path.startswith('/openapi.json'):
            return '/openapi.json'
        else:
            return path

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address considering proxies."""
        # Check for forwarded headers (common in production deployments)
        forwarded_for = request.headers.get('x-forwarded-for')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        
        real_ip = request.headers.get('x-real-ip')
        if real_ip:
            return real_ip
            
        return request.client.host if request.client else 'unknown'

    def _sanitize_query_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize query parameters to avoid logging sensitive data."""
        # For YouTube endpoint, we want to log query content for analysis
        # but avoid any potential sensitive data
        sanitized = {}
        for key, value in params.items():
            if key.lower() in ['query', 'max_results', 'transcript_language', 'order_by']:
                # Log YouTube search parameters as they're needed for analysis
                sanitized[key] = value
            elif key.lower() in ['published_after', 'published_before']:
                # Log date filters
                sanitized[key] = value
            else:
                # Sanitize any other parameters
                sanitized[key] = '[REDACTED]'
        return sanitized

    def _classify_error_by_status(self, status_code: int) -> str:
        """Classify errors based on HTTP status codes."""
        if status_code == 400:
            return 'validation_error'
        elif status_code == 404:
            return 'not_found_error'
        elif status_code == 413:
            return 'payload_too_large_error'
        elif status_code == 429:
            return 'rate_limit_error'
        elif 400 <= status_code < 500:
            return 'client_error'
        elif status_code >= 500:
            return 'internal_error'
        else:
            return 'unknown_error'

    def _classify_error_by_exception(self, exception: Exception) -> str:
        """Classify errors based on exception types."""
        exception_name = type(exception).__name__
        
        # YouTube-specific errors
        if 'YouTubeApiError' in exception_name:
            return 'youtube_api_error'
        elif 'YouTubeClientError' in exception_name:
            return 'youtube_client_error'
        elif 'YouTubeTranscriptError' in exception_name:
            return 'youtube_transcript_error'
        
        # General validation errors
        elif 'ValidationError' in exception_name or 'ValueError' in exception_name:
            return 'validation_error'
        
        # HTTP and network errors
        elif 'HTTPException' in exception_name:
            return 'http_error'
        elif 'TimeoutError' in exception_name or 'Timeout' in exception_name:
            return 'timeout_error'
        
        # Catch-all for unexpected errors
        else:
            return 'internal_error'

    def _update_metrics(self, method: str, path: str, status_code: int, duration: float, error_type: Optional[str]):
        """Update all Prometheus metrics."""
        try:
            # Update request count
            youtube_mcp_request_count.labels(
                method=method,
                path=path,
                status_code=str(status_code)
            ).inc()

            # Update request latency
            youtube_mcp_request_latency_seconds.labels(
                method=method,
                path=path
            ).observe(duration)

            # Update error metrics if this was an error
            if error_type:
                youtube_mcp_error_count.labels(
                    method=method,
                    path=path,
                    error_type=error_type
                ).inc()
                
                youtube_mcp_error_count_total.labels(
                    method=method,
                    path=path
                ).inc()

        except Exception as e:
            # Never let metrics collection break the application
            logger.error(f"Failed to update metrics: {e}", exc_info=True)


def get_metrics_response() -> StarletteResponse:
    """Generate Prometheus metrics response for /metrics endpoint."""
    try:
        metrics_data = generate_latest()
        return StarletteResponse(
            content=metrics_data,
            media_type=CONTENT_TYPE_LATEST,
            headers={'Cache-Control': 'no-cache'}
        )
    except Exception as e:
        logger.error(f"Failed to generate metrics: {e}", exc_info=True)
        return StarletteResponse(
            content='# Metrics generation failed\n',
            status_code=500,
            media_type='text/plain'
        )