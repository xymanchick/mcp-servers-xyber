"""
FastAPI dependency injection for the Cartesia MCP Server.

Main responsibility: Provide dependency injection functions for shared resources.
"""

from functools import lru_cache

from mcp_server_cartesia.cartesia_client import (
    _CartesiaService,
    get_cartesia_service as _get_cartesia_service,
)


@lru_cache(maxsize=1)
def get_cartesia_service() -> _CartesiaService:
    """
    Dependency injection function to get the Cartesia service.

    This function is cached to ensure only one instance of the service
    is created and reused across requests.

    Returns:
        An initialized _CartesiaService instance.

    Raises:
        CartesiaConfigError: If configuration loading or validation fails.
        CartesiaClientError: If the Cartesia library isn't installed.
    """
    return _get_cartesia_service()
