from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from enum import StrEnum
from typing import Any

from mcp.server import Server
from mcp.types import TextContent, Tool
from mcp_server_postgres.postgres_client import (
    Agent,
    PostgresServiceError,
    _PostgresService,
    get_postgres_service,
)
from pydantic import BaseModel, Field, ValidationError

# Get module-level logger
logger = logging.getLogger(__name__)

# --- Tool Input/Output Schemas --- #


class GetCharacterByNameRequest(BaseModel):
    """Input schema for the get_character_by_name tool."""

    name: str = Field(..., description="The unique name of the character to retrieve.")


class PostgresMCPServerTools(StrEnum):
    GET_CHARACTER_BY_NAME = "get_character_by_name"


# --- Lifespan Management for MCP Server --- #
@asynccontextmanager
async def server_lifespan(server_instance: Server) -> AsyncIterator[dict[str, Any]]:
    """
    Manage MCP server startup/shutdown. Initializes the PostgreSQL service.
    """
    logger.info("MCP Lifespan: Initializing PostgreSQL service...")
    try:
        db_service = get_postgres_service()
        logger.info("MCP Lifespan: PostgreSQL service initialized successfully.")

        yield {"db_service": db_service}
    except Exception as e:
        logger.error(f"FATAL: MCP Lifespan initialization failed: {e}", exc_info=True)
        raise
    finally:
        logger.info("MCP Lifespan: Shutdown cleanup (if any).")


# --- MCP Server Initialization --- #
server = Server("postgres-mcp-server", lifespan=server_lifespan)


# --- Tool Definitions --- #
@server.list_tools()
async def list_tools() -> list[Tool]:
    """Lists the tools available in this MCP server."""
    logger.debug("Listing available tools.")
    return [
        Tool(
            name="get_character_by_name",
            description="Retrieves a character record from the database based on its unique name.",
            inputSchema=GetCharacterByNameRequest.model_json_schema(),
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handles incoming tool calls."""
    logger.info(f"Received call_tool request for '{name}' with args: {arguments}")

    db_service: _PostgresService = server.request_context.lifespan_context.get(
        "db_service"
    )

    match name:
        case PostgresMCPServerTools.GET_CHARACTER_BY_NAME.value:
            try:
                # 1. Validate Input Arguments
                request_model = GetCharacterByNameRequest(**arguments)
                character_name = request_model.name

                # 2. Execute Core Logic
                logger.info(f"Querying database for character: {character_name}")
                agent: Agent = await db_service.get_agent_by_name(name=character_name)

                # 3. Format Response
                logger.info(f"Successfully retrieved character: {agent.name}")
                result_content: list[TextContent] = []

                result_content.append(TextContent(type="text", text=f"{agent}"))

            except ValidationError as ve:
                error_msg = f"Invalid arguments for tool '{name}': {ve}"
                logger.warning(error_msg)
                return [TextContent(type="text", text=error_msg)]

            except PostgresServiceError as db_err:
                error_msg = f"Database error processing tool '{name}': {db_err}"
                logger.error(error_msg, exc_info=True)
                return [TextContent(type="text", text=error_msg)]

            except Exception as e:
                error_msg = (
                    f"An unexpected internal error occurred processing tool '{name}'."
                )
                logger.error(f"{error_msg} Details: {e}", exc_info=True)
                return [TextContent(type="text", text=error_msg)]

        case _:
            logger.warning(f"Received call for unknown tool: {name}")
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
