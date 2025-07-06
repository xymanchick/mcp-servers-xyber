## This file structure should stay the same for all MCP servers
## It is responsible for defining the MCP server and its tools
## But the exact content (lifespan server, tool definitions, etc)
## Should be edited to fit your needs

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, Literal

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError

# --- Calculator Module Imports ---
from mcp_server_calculator.calculator import (
    CalculatorClient,
    CalculatorError,
    get_calculator_client,
)

logger = logging.getLogger(__name__)


# --- Lifespan Management for MCP Server --- #
# Lifespan is usually used for initializing and cleaning up resources
# when using some external API's or Databases
#
# It also can be used for stroing shared dependencies, like in this case
# (A single CalculatorClient instance is being shared)


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[dict[str, Any]]:
    """Manage server startup/shutdown. Initializes required services."""
    logger.info("Lifespan: Initializing services...")

    try:
        # Initialize Calculator Client
        calculator_client: CalculatorClient = get_calculator_client()

        logger.info("Lifespan: Services initialized successfully.")
        yield {"calculator_client": calculator_client}

    except CalculatorError as init_err:
        logger.error(
            f"FATAL: Lifespan initialization failed: {init_err}", exc_info=True
        )
        raise init_err

    except Exception as startup_err:
        logger.error(
            f"FATAL: Unexpected error during lifespan initialization: {startup_err}",
            exc_info=True,
        )
        raise startup_err

    finally:
        logger.info("Lifespan: Shutdown cleanup (if any).")


# --- MCP Server Initialization --- #

mcp_server = FastMCP("calculator-server", lifespan=app_lifespan)


# --- Tool Definitions --- #
# Feel free to add more tools here!


@mcp_server.tool()
def calculate(
    operation: Literal["add", "subtract", "multiply", "divide"],
    operand1: float,
    operand2: float,
    ctx: Context,
) -> str:
    """Calculate the result of an arithmetic operation."""
    calculator_client = ctx.request_context.lifespan_context["calculator_client"]

    try:
        result = calculator_client.calculate(
            operation=operation,
            operand1=operand1,
            operand2=operand2,
        )

        logger.info(f"Successfully processed '{operation}' request. Result: {result}")
        return f"Calculation result: {result}"

    except CalculatorError as calc_base_err:
        logger.error(f"A calculator error occurred: {calc_base_err}")
        raise ToolError(
            f"A calculator error occurred: {calc_base_err}"
        ) from calc_base_err

    except Exception as e:
        logger.error(f"Unexpected error processing tool calculate: {e}", exc_info=True)
        raise ToolError(
            "An unexpected error occurred processing tool calculate."
        ) from e
