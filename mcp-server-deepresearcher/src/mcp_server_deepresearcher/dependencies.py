"""
FastAPI dependencies for accessing shared resources from app state.
"""

import logging

from mcp_server_deepresearcher.deepresearcher.state import ToolDescription

logger = logging.getLogger(__name__)


class DependencyContainer:
    """
    Centralized container for all application dependencies.

    Usage:
        # In app.py lifespan:
        await DependencyContainer.initialize()

    Yield:
        await DependencyContainer.shutdown()

        # In route handlers via helper function:
        resources = get_research_resources()

    """

    _llm = None
    _llm_thinking = None
    _mcp_tools: list = []
    _tools_description: list[ToolDescription] = []
    _mcp_connection_error: str | None = None

    @classmethod
    async def initialize(
        cls,
        llm,
        llm_thinking,
        mcp_tools: list,
        tools_description: list[ToolDescription],
        mcp_connection_error: str | None = None,
    ) -> None:
        """
        Initialize all dependencies.

        Call this once during application startup (in lifespan).
        """
        logger.info("Initializing dependencies...")

        cls._llm = llm
        cls._llm_thinking = llm_thinking
        cls._mcp_tools = mcp_tools
        cls._tools_description = tools_description
        cls._mcp_connection_error = mcp_connection_error

        logger.info("Dependencies initialized successfully.")

    @classmethod
    async def shutdown(cls) -> None:
        """
        Shut down all dependencies gracefully.

        Call this once during application shutdown (in lifespan).
        """
        logger.info("Shutting down dependencies...")

        cls._llm = None
        cls._llm_thinking = None
        cls._mcp_tools = []
        cls._tools_description = []
        cls._mcp_connection_error = None

        logger.info("Dependencies shut down successfully.")

    @classmethod
    def get_research_resources(cls) -> dict:
        """
        Get research resources for route handlers.

        Returns a dictionary containing all research-related resources.
        """
        if cls._llm is None:
            raise RuntimeError(
                "DependencyContainer not initialized. Call DependencyContainer.initialize() first."
            )
        return {
            "llm": cls._llm,
            "llm_thinking": cls._llm_thinking,
            "mcp_tools": cls._mcp_tools,
            "tools_description": cls._tools_description,
            "mcp_connection_error": cls._mcp_connection_error,
        }


# Alias the class method for use as FastAPI dependency
get_research_resources = DependencyContainer.get_research_resources
