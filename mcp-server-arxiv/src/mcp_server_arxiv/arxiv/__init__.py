"""Arxiv client module for the MCP server."""

from mcp_server_arxiv.arxiv.config import (
    ArxivApiError,
    ArxivConfig,
    ArxivConfigError,
    ArxivServiceError,
)
from mcp_server_arxiv.arxiv.models import ArxivSearchResult
from mcp_server_arxiv.arxiv.module import _ArxivService, get_arxiv_service

__all__ = [
    "_ArxivService",
    "get_arxiv_service",
    "ArxivSearchResult",
    "ArxivConfig",
    "ArxivServiceError",
    "ArxivApiError",
    "ArxivConfigError",
]
