import logging

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from mcp_server_telegram_parser.schemas import TelegramParseResult
from mcp_server_telegram_parser.telegram.module import get_parser_service

logger = logging.getLogger(__name__)

mcp_server = FastMCP(name="telegram-parser")


@mcp_server.tool()
async def parse_telegram_channels(
    ctx: Context, channels: list[str], limit: int = 10
) -> TelegramParseResult:
    """Parse last N messages from provided public Telegram channels using Telethon."""
    try:
        service = get_parser_service()
        return await service.parse_channels(channels=channels, limit=limit)
    except Exception as e:
        logger.error("Parsing failed: %s", str(e), exc_info=True)
        raise ToolError("Failed to parse telegram channels") from e
