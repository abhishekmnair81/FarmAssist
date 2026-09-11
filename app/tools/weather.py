import httpx
from typing import Dict, Any, Tuple
from app.config import settings
import logging

logger = logging.getLogger(__name__)

async def geocode(location: str) -> Tuple[float, float]:
    """
    Resolve a location string to latitude and longitude using Open-Meteo Geocoding API.
    """
    url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {
        "name": location,
        "count": 1,
        "format": "json"
    }
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        results = data.get("results")
        if not results:
            raise ValueError(f"Could not find coordinates for location: {location}")
            
        lat = float(results[0]["latitude"])
        lon = float(results[0]["longitude"])
        return lat, lon

async def get_weather(location_name: str = None, lat: float = None, lon: float = None) -> Dict[str, Any]:
    """
    Retrieves agricultural weather parameters from Open-Meteo.
    Prioritizes explicitly passed lat/lon. If a location_name is passed, resolves it.
    If neither are provided, uses the .env default as a last resort fallback.
    """
    resolved_lat = lat
    resolved_lon = lon
    
    if location_name and (resolved_lat is None or resolved_lon is None):
        try:
            resolved_lat, resolved_lon = await geocode(location_name)
        except Exception as e:
            logger.error(f"Geocoding failed for {location_name}: {e}")
            return {"error": str(e)}
            
    if resolved_lat is None or resolved_lon is None:
        resolved_lat = settings.DEFAULT_LAT
        resolved_lon = settings.DEFAULT_LON

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": resolved_lat,
        "longitude": resolved_lon,
        "current": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m",
        "hourly": "soil_moisture_0_to_1cm,soil_temperature_0cm",
        "daily": "precipitation_sum,precipitation_probability_max,temperature_2m_max,temperature_2m_min,wind_speed_10m_max,wind_gusts_10m_max",
        "timezone": "auto"
    }
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        return {
            "location_coords": {"lat": resolved_lat, "lon": resolved_lon},
            "current": data.get("current", {}),
            "daily_forecast": data.get("daily", {}),
            "soil_conditions_next_24h": {
                "moisture_surface": data.get("hourly", {}).get("soil_moisture_0_to_1cm", [])[:24],
                "temperature_surface": data.get("hourly", {}).get("soil_temperature_0cm", [])[:24]
            }
        }
