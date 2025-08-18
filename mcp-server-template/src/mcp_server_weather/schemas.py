from pydantic import BaseModel, Field
from typing import Literal


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
