import logging
import time
from collections import defaultdict, deque
from collections.abc import Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from functools import wraps
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class OperationMetrics:
    """Metrics for a specific operation."""

    name: str
    total_calls: int = 0
    total_duration_ms: float = 0.0
    min_duration_ms: float = float("inf")
    max_duration_ms: float = 0.0
    success_count: int = 0
    error_count: int = 0
    recent_durations: deque = field(default_factory=lambda: deque(maxlen=100))
    last_called: datetime | None = None

    @property
    def avg_duration_ms(self) -> float:
        """Calculate average duration."""
        if self.total_calls == 0:
            return 0.0
        return self.total_duration_ms / self.total_calls

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_calls == 0:
            return 0.0
        return (self.success_count / self.total_calls) * 100

    @property
    def p95_duration_ms(self) -> float:
        """Calculate 95th percentile duration."""
        if not self.recent_durations:
            return 0.0
        sorted_durations = sorted(self.recent_durations)
        index = int(0.95 * len(sorted_durations))
        return sorted_durations[min(index, len(sorted_durations) - 1)]


class MetricsCollector:
    """Centralized metrics collection and reporting."""

    def __init__(self):
        self.operations: dict[str, OperationMetrics] = defaultdict(
            lambda: OperationMetrics(name="unknown")
        )
        self._start_time: datetime = datetime.now(UTC)

    def record_operation(
        self,
        operation_name: str,
        duration_ms: float,
        success: bool = True,
        context: dict[str, Any] | None = None,
    ):
        """Record metrics for an operation."""
        metrics = self.operations[operation_name]
        metrics.name = operation_name
        metrics.total_calls += 1
        metrics.total_duration_ms += duration_ms
        metrics.min_duration_ms = min(metrics.min_duration_ms, duration_ms)
        metrics.max_duration_ms = max(metrics.max_duration_ms, duration_ms)
        metrics.recent_durations.append(duration_ms)
        metrics.last_called = datetime.now(UTC)

        if success:
            metrics.success_count += 1
        else:
            metrics.error_count += 1

    def get_operation_metrics(self, operation_name: str) -> OperationMetrics:
        """Get metrics for a specific operation."""
        return self.operations.get(operation_name, OperationMetrics(operation_name))

    def get_all_metrics(self) -> dict[str, dict[str, Any]]:
        """Get all collected metrics as a dictionary."""
        now = datetime.now(UTC)
        result = {
            "server_uptime_seconds": (now - self._start_time).total_seconds(),
            "operations": {},
        }

        for op_name, metrics in self.operations.items():
            result["operations"][op_name] = {
                "total_calls": metrics.total_calls,
                "success_count": metrics.success_count,
                "error_count": metrics.error_count,
                "success_rate_percent": round(metrics.success_rate, 2),
                "avg_duration_ms": round(metrics.avg_duration_ms, 2),
                "min_duration_ms": round(metrics.min_duration_ms, 2),
                "max_duration_ms": round(metrics.max_duration_ms, 2),
                "p95_duration_ms": round(metrics.p95_duration_ms, 2),
                "last_called": metrics.last_called.isoformat()
                if metrics.last_called
                else None,
            }

        return result

    def log_summary(self):
        """Log a summary of all metrics."""
        pass


# Global metrics collector instance
_metrics_collector = MetricsCollector()


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector instance."""
    return _metrics_collector


@asynccontextmanager
async def async_operation_timer(
    operation_name: str, context: dict[str, Any] | None = None
):
    """Async context manager for timing operations."""
    start_time = time.perf_counter()
    success = True

    try:
        yield
    except Exception as e:
        success = False
        logger.error(
            f"Operation failed: {operation_name}",
            extra={"operation": operation_name, "error": str(e), **(context or {})},
            exc_info=True,
        )
        raise
    finally:
        duration_ms = (time.perf_counter() - start_time) * 1000
        _metrics_collector.record_operation(
            operation_name, duration_ms, success, context
        )


def async_timed(operation_name: str | None = None):
    """Decorator for timing async functions."""

    def decorator(func: Callable):
        op_name = operation_name or f"{func.__module__}.{func.__name__}"

        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract context from function arguments if available
            context = {}
            if hasattr(func, "__annotations__"):
                # Try to extract meaningful context from arguments
                if "user_id" in kwargs:
                    context["user_id"] = kwargs["user_id"]
                if "tweet_id" in kwargs:
                    context["tweet_id"] = kwargs["tweet_id"]

            async with async_operation_timer(op_name, context):
                return await func(*args, **kwargs)

        return wrapper

    return decorator


def sync_timed(operation_name: str | None = None):
    """Decorator for timing synchronous functions."""

    def decorator(func: Callable):
        op_name = operation_name or f"{func.__module__}.{func.__name__}"

        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            success = True

            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                logger.error(
                    f"Operation failed: {op_name}",
                    extra={"operation": op_name, "error": str(e)},
                    exc_info=True,
                )
                raise
            finally:
                duration_ms = (time.perf_counter() - start_time) * 1000
                _metrics_collector.record_operation(op_name, duration_ms, success)

                log_level = logging.DEBUG
                if not success:
                    log_level = logging.ERROR
                elif duration_ms > 1000:
                    log_level = logging.WARNING

                logger.log(
                    log_level,
                    f"Operation completed: {op_name} in {duration_ms:.2f}ms",
                    extra={
                        "operation": op_name,
                        "duration_ms": round(duration_ms, 2),
                        "success": success,
                    },
                )

        return wrapper

    return decorator


class HealthChecker:
    """Manages the health status and uptime of the server."""

    def __init__(self, metrics: MetricsCollector):
        self.metrics = metrics
        self._start_time: datetime = datetime.now(UTC)

    def get_health_status(self) -> dict[str, Any]:
        """Get comprehensive health status."""
        now = datetime.now(UTC)
        uptime = (now - self._start_time).total_seconds()

        health_status = {
            "status": "healthy",
            "timestamp": now.isoformat(),
            "uptime_seconds": round(uptime, 1),
            "checks": {},
        }

        # Check if we have recent activity
        recent_activity = False
        for op_metrics in self.metrics.operations.values():
            if op_metrics.last_called and now - op_metrics.last_called < timedelta(
                minutes=5
            ):
                recent_activity = True
                break

        health_status["checks"]["recent_activity"] = {
            "status": "pass" if recent_activity else "warn",
            "message": "Recent activity detected"
            if recent_activity
            else "No recent activity",
        }

        # Check error rates
        high_error_rate = False
        for op_name, op_metrics in self.metrics.operations.items():
            if op_metrics.total_calls > 10 and op_metrics.success_rate < 50:
                high_error_rate = True
                health_status["checks"]["error_rate"] = {
                    "status": "fail",
                    "message": f"High error rate in {op_name}: {op_metrics.success_rate:.1f}%",
                }
                break

        if not high_error_rate:
            health_status["checks"]["error_rate"] = {
                "status": "pass",
                "message": "Error rates are within acceptable limits",
            }

        # Overall status
        failed_checks = [
            check
            for check in health_status["checks"].values()
            if check["status"] == "fail"
        ]

        if failed_checks:
            health_status["status"] = "unhealthy"
        elif any(
            check["status"] == "warn" for check in health_status["checks"].values()
        ):
            health_status["status"] = "degraded"

        return health_status


# Global health checker instance
_health_checker = HealthChecker(_metrics_collector)


def get_health_checker() -> HealthChecker:
    """Get the global health checker instance."""
    return _health_checker
