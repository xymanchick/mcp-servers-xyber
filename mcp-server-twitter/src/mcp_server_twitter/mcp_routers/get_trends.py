import json
import logging

from fastapi import APIRouter, Depends
from fastmcp.exceptions import ToolError
from pydantic import ValidationError

from mcp_server_twitter.dependencies import get_twitter_client_dep
from mcp_server_twitter.errors import TwitterMCPError
from mcp_server_twitter.logging_config import get_logger
from mcp_server_twitter.metrics import async_timed
from mcp_server_twitter.schemas import GetTrendsRequest

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/get-trends",
    tags=["Twitter"],
    operation_id="twitter_get_trends",
)
@async_timed("get_trends")
async def get_trends(
    trends_request: GetTrendsRequest,
    client: AsyncTwitterClient = Depends(get_twitter_client_dep),
) -> str:
    """Get trends with comprehensive logging."""
    operation_logger = get_logger(
        f"{__name__}.get_trends",
        operation="get_trends",
        country_count=len(trends_request.countries),
        max_trends=trends_request.max_trends,
    )

    operation_logger.info(
        "Trends retrieval requested",
        extra={
            "countries": trends_request.countries,
            "max_trends_per_country": trends_request.max_trends,
        },
    )

    try:
        operation_logger.debug("Calling Twitter API to retrieve trends")
        trends = await client.get_trends(
            countries=trends_request.countries, max_trends=trends_request.max_trends
        )

        operation_logger.info(
            "Trends retrieved successfully",
            extra={
                "countries_processed": len(trends),
                "total_trends": sum(
                    len(country_trends)
                    for country_trends in trends.values()
                    if isinstance(country_trends, list)
                ),
            },
        )

        return json.dumps(trends, ensure_ascii=False, indent=2)

    except TwitterMCPError as e:
        operation_logger.error(
            "A known Twitter MCP error occurred while retrieving trends",
            extra={"error_type": type(e).__name__, "error_code": e.error_code},
            exc_info=True,
        )
        raise ToolError(f"Error retrieving trends: {str(e)}") from e
    except ValidationError as e:
        operation_logger.warning(
            "Input validation failed", extra={"errors": e.errors()}
        )
        raise ToolError(f"Invalid input: {e}") from e
    except Exception as e:
        operation_logger.error(
            "Unexpected error while retrieving trends",
            extra={"error_type": type(e).__name__},
            exc_info=True,
        )
        raise ToolError(
            f"An unexpected error occurred while retrieving trends: {str(e)}"
        ) from e
