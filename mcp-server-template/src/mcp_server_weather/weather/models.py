"""Weather data models with modern Python 3.12+ features."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class WeatherData:
    """Immutable weather data model."""
    
    state: str
    temperature: str
    humidity: str
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> WeatherData:
        """Create a WeatherData instance from API response.
        
        Args:
            data: Raw API response data from OpenWeatherMap
            
        Returns:
            Structured WeatherData object
            
        Raises:
            KeyError: If required fields are missing from the response
        """
        try:
            return cls(
                state=data["weather"][0]["description"],
                temperature=f"{data['main']['temp']}C",
                humidity=f"{data['main']['humidity']}%",
            )
        except KeyError as e:
            raise KeyError(f"Missing required field in weather data: {e}") from e
    