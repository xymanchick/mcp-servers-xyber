import logging

from fastapi import APIRouter
from mcp_server_twitter.metrics import (get_health_checker,
                                        get_metrics_collector)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/health",
    tags=["Health"],
    operation_id="health_check",
)
async def get_health() -> dict:
    """Get server health status and metrics."""
    health_checker = get_health_checker()
    health_status = health_checker.get_health_status()

    logger.debug("Health status requested", extra={"health_status": health_status})

    return health_status


@router.get(
    "/metrics",
    tags=["Health"],
    operation_id="get_metrics",
)
async def get_metrics() -> dict:
    """Get server performance metrics."""
    metrics_collector = get_metrics_collector()
    metrics = metrics_collector.get_all_metrics()

    logger.debug("Metrics requested", extra={"metrics_summary": metrics})

    return metrics
