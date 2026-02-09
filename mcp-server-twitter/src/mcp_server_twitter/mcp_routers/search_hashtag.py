import json
import logging

from fastapi import APIRouter, Request
from fastmcp.exceptions import ToolError
from mcp_server_twitter.errors import TwitterMCPError
from mcp_server_twitter.logging_config import get_logger
from mcp_server_twitter.metrics import async_timed
from mcp_server_twitter.schemas import SearchHashtagRequest
from pydantic import ValidationError

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/search-hashtag",
    tags=["Twitter"],
    operation_id="twitter_search_hashtag",
)
@async_timed("search_hashtag")
async def search_hashtag(
    search_request: SearchHashtagRequest,
    request: Request,
) -> str:
    """Search hashtag with comprehensive logging."""
    operation_logger = get_logger(
        f"{__name__}.search_hashtag",
        operation="search_hashtag",
        hashtag=search_request.hashtag,
        max_results=search_request.max_results,
    )

    operation_logger.info(
        f"Hashtag search requested for #{search_request.hashtag}",
        extra={"max_results": search_request.max_results},
    )

    client = request.app.state.twitter_client

    try:
        operation_logger.debug(
            f"Calling Twitter API to search hashtag #{search_request.hashtag}"
        )
        tweets = await client.search_hashtag(
            hashtag=search_request.hashtag, max_results=search_request.max_results
        )

        operation_logger.info(
            f"Hashtag search completed for #{search_request.hashtag}",
            extra={"tweets_found": len(tweets)},
        )

        return json.dumps(tweets, ensure_ascii=False, indent=2)

    except TwitterMCPError as e:
        operation_logger.error(
            f"A known Twitter MCP error occurred while searching hashtag #{search_request.hashtag}",
            extra={"error_type": type(e).__name__, "error_code": e.error_code},
            exc_info=True,
        )
        raise ToolError(f"Error searching hashtag: {str(e)}") from e
    except ValidationError as e:
        operation_logger.warning(
            "Input validation failed", extra={"errors": e.errors()}
        )
        raise ToolError(f"Invalid input: {e}") from e
    except Exception as e:
        operation_logger.error(
            f"Unexpected error searching hashtag #{search_request.hashtag}",
            extra={"error_type": type(e).__name__},
            exc_info=True,
        )
        raise ToolError(
            f"An unexpected error occurred while searching for a hashtag: {str(e)}"
        ) from e
