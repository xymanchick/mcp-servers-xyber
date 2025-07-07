"""
PostgreSQL client interface providing access to database entities.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from functools import lru_cache

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mcp_server_postgres.postgres_client.config import (
    PostgresAPIError,
    PostgresConfig,
    PostgresConfigError,
)
from mcp_server_postgres.postgres_client.database import async_session_maker
from mcp_server_postgres.postgres_client.models.character_model import Agent


class _PostgresService:
    """
    Client for PostgreSQL database operations.
    Provides a simplified interface for common database operations.
    """

    def __init__(
        self, config: PostgresConfig, session_factory: Callable[[], AsyncSession]
    ) -> None:
        """
        Initialize the PostgreSQL client.

        Args:
            config: PostgreSQL connection configuration
            session_factory: Factory function that returns a new database session

        """
        self.config = config
        self.session_factory = session_factory

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        """
        Context manager for database sessions with proper error handling.

        Automatically handles rollback on error and ensures session is closed.

        Yields:
            AsyncSession: Database session

        """
        session = self.session_factory()
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()

    async def get_agent_by_name(self, name: str) -> Agent | None:
        """
        Get an agent by its unique name.

        Args:
            name: The unique name of the agent

        Returns:
            The agent if found, None if not found.

        Raises:
            PostgresAPIError: If there is an error during database query.

        """
        try:
            async with self.session() as session:
                stmt = select(Agent).where(Agent.name == name)
                result = await session.execute(stmt)
                agent = result.scalars().first()
                return agent
        except Exception as e:
            raise PostgresAPIError(
                f"Failed to get agent by name '{name}': {str(e)}", e
            ) from e

    async def get_agent_by_ticker(self, ticker: str) -> Agent | None:
        """
        Get an agent by its unique ticker.

        Args:
            ticker: The unique ticker of the agent

        Returns:
            The agent if found, None if not found.

        Raises:
            PostgresAPIError: If there is an error during database query.

        """
        try:
            async with self.session() as session:
                stmt = select(Agent).where(Agent.ticker == ticker)
                result = await session.execute(stmt)
                agent = result.scalars().first()
                return agent
        except Exception as e:
            raise PostgresAPIError(
                f"Failed to get agent by ticker '{ticker}': {str(e)}", e
            ) from e

    async def get_all_agents(self, limit: int = 100, offset: int = 0) -> list[Agent]:
        """
        Get all agents with pagination.

        Args:
            limit: Maximum number of agents to return
            offset: Number of agents to skip

        Returns:
            A list of agents. Returns an empty list if no agents are found.

        Raises:
            PostgresAPIError: If there is an error during database query.

        """
        try:
            async with self.session() as session:
                stmt = select(Agent).limit(limit).offset(offset)
                result = await session.execute(stmt)
                agents = result.scalars().all()
                return list(agents)
        except Exception as e:
            raise PostgresAPIError(
                f"Failed to get all agents (limit={limit}, offset={offset}): {str(e)}",
                e,
            ) from e


@lru_cache(maxsize=1)
def get_postgres_service() -> _PostgresService:
    """
    Get a singleton instance of the PostgreSQL client.
    This function is cached to return the same instance for multiple calls.

    Returns:
        The PostgreSQL client instance.

    Raises:
        PostgresConfigError: If there is an error initializing the client or its configuration.

    """
    try:
        config = PostgresConfig()
        return _PostgresService(config=config, session_factory=async_session_maker)
    except Exception as e:
        raise PostgresConfigError(
            f"Failed to initialize PostgreSQL client: {str(e)}", e
        ) from e
