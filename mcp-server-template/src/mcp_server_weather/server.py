## This file structure should stay the same for all MCP servers
## It is responsible for defining the MCP server and its tools
## But the exact content (lifespan server, tool definitions, etc)
## Should be edited to fit your needs

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Any, Literal

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from pydantic import BaseModel, Field, ValidationError as PydanticValidationError

from mcp_server_weather.weather import (
    WeatherClient,
    WeatherError,
    WeatherApiError,
    WeatherClientError,
    get_weather_client,
)

logger = logging.getLogger(__name__)

# --- Custom Exceptions --- #
class ValidationError(ToolError):
    """Custom exception for input validation failures."""

    def __init__(self, message: str, code: str = "VALIDATION_ERROR"):
        self.message = message
        self.code = code
        self.status_code = 400
        super().__init__(message)
        
        
# --- Input Validation Schemas --- #

class LocationRequest(BaseModel):
    """Input schema for location-based queries with unit preferences."""

    latitude: str = Field(
        ...,
        regex=r"^-?\d{1,2}\.\d+$",
        description="Location latitude as a string, e.g., '37.7749'. Format: decimal degrees with optional negative sign",
    )
    longitude: str = Field(
        ...,
        regex=r"^-?\d{1,3}\.\d+$",
        description="Location longitude as a string, e.g., '-122.4194'. Format: decimal degrees with optional negative sign",
    )
    units: Literal["metric", "imperial"] | None = Field(
        default=None,
        description="Unit system for temperature and other measures: 'metric' or 'imperial'. Defaults to configuration.",
    )


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
    latitude: str,
    longitude: str, 
    units: str | None = None,
) -> dict[str, str]:
    """Get current weather data for a location.
    
    Args:
        latitude: Location latitude 
        longitude: Location longitude
        units: Unit system (metric or imperial, defaults to configuration)
        
    Returns:
        Dictionary with weather state, temperature, and humidity
        
    Raises:
        ToolError: If weather retrieval fails
    """
    weather_client = ctx.request_context.lifespan_context["weather_client"]

    try:
        # Validate input payload against the request schema
        LocationRequest(
            latitude=latitude,
            longitude=longitude,
            units=units
        )
        
        # Get weather data from client
        weather_data = await weather_client.get_weather(
            latitude=latitude,
            longitude=longitude,
            units = units
        )

        # Format response
        result = {
            "state": weather_data.state,
            "temperature": weather_data.temperature,
            "humidity": weather_data.humidity,
        }

        logger.info(f"Successfully retrieved weather data: {result}")
        return result

    except PydanticValidationError as ve:
        logger.warning(f"Validation error: {ve}")
        error_details = "; ".join(
            f"{err['loc'][0]}: {err['msg']}" for err in ve.errors()
        )
        raise ValidationError(f"Invalid parameters: {error_details}")
    
    except WeatherApiError as api_err:
        logger.error(f"Weather API error: {api_err}")
        raise ToolError(f"Weather API error: {api_err}") from api_err

    except WeatherClientError as client_err:
        logger.error(f"Weather client error: {client_err}")
        raise ToolError(f"Weather client error: {client_err}") from client_err

    except Exception as e:
        logger.error(f"Unexpected error processing tool get_weather: {e}", exc_info=True)
        raise ToolError(
            "An unexpected error occurred processing weather request"
        ) from e
