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

from mcp_server_weather.weather import (
    WeatherApiError,
    WeatherClient,
    WeatherClientError,
    WeatherError,
    get_weather_client,
)
from mcp_server_weather.schemas import LocationRequest

logger = logging.getLogger(__name__)

# --- Custom Exceptions --- #


# --- Input Validation Schemas --- #


# --- Lifespan Management for MCP Server --- #
# Lifespan is usually used for initializing and cleaning up resources
# when using some external API's or Databases
#
# It also can be used for stroing shared dependencies, like in this case
# (A single CalculatorClient instance is being shared)


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[dict[str, Any]]:
    """Manage server startup/shutdown. Initializes required services.

    Args:
        server: The FastMCP server instance

    Yields:
        Dictionary with initialized services

    Raises:
        WeatherError: If service initialization fails
    """
    logger.info("Lifespan: Initializing services...")

    try:
        # Initialize Weather Client
        weather_client: WeatherClient = get_weather_client()

        logger.info("Lifespan: Services initialized successfully")
        yield {"weather_client": weather_client}

    except WeatherError as init_err:
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
        try:
            # Clean up resources
            await weather_client.close()
            logger.info("Lifespan: Closed weather client session")

        except Exception as e:
            logger.error(f"Error closing weather client: {e}")

        logger.info("Lifespan: Shutdown cleanup completed")


# --- MCP Server Initialization --- #
mcp_server = FastMCP("weather-server", lifespan=app_lifespan)


# --- Tool Definitions --- #
# Feel free to add more tools here!


@mcp_server.tool()
async def get_weather(
    ctx: Context,
    request: LocationRequest,
) -> dict[str, str]:
    """Get current weather data for a location.

    Args:
        request: LocationRequest containing latitude, longitude, and optional units

    Returns:
        Dictionary with weather state, temperature, and humidity

    Raises:
        ToolError: If weather retrieval fails
    """
    weather_client = ctx.request_context.lifespan_context["weather_client"]

    try:
        # Get weather data from client using validated request data
        weather_data = await weather_client.get_weather(
            latitude=request.latitude, longitude=request.longitude, units=request.units
        )

        # Format response
        result = {
            "state": weather_data.state,
            "temperature": weather_data.temperature,
            "humidity": weather_data.humidity,
        }

        logger.info(f"Successfully retrieved weather data: {result}")
        return result

    except WeatherApiError as api_err:
        logger.error(f"Weather API error: {api_err}")
        raise ToolError(f"Weather API error: {api_err}") from api_err

    except WeatherClientError as client_err:
        logger.error(f"Weather client error: {client_err}")
        raise ToolError(f"Weather client error: {client_err}") from client_err

    except Exception as e:
        logger.error(
            f"Unexpected error processing tool get_weather: {e}", exc_info=True
        )
        raise ToolError(
            "An unexpected error occurred processing weather request"
        ) from e
