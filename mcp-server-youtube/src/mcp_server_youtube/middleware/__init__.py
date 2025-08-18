"""
Middleware package for YouTube MCP server.

This package contains middleware components for:
- Performance monitoring and metrics collection
- Request tracing and correlation
- Error classification and logging
"""

from .performance_metrics import PerformanceMetricsMiddleware, get_metrics_response

__all__ = [
    'PerformanceMetricsMiddleware',
    'get_metrics_response',
]