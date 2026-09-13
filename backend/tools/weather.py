import httpx
from typing import Dict, Any

# WMO Weather interpretation codes
WEATHER_CODES = {
    0: "Clear sky ☀️",
    1: "Mainly clear 🌤️",
    2: "Partly cloudy ⛅",
    3: "Overcast ☁️",
    45: "Fog 🌫️",
    48: "Depositing rime fog 🌫️",
    51: "Light drizzle 🌦️",
    53: "Moderate drizzle 🌧️",
    55: "Dense drizzle 🌧️",
    61: "Slight rain 🌦️",
    63: "Moderate rain 🌧️",
    65: "Heavy rain ⛈️",
    71: "Slight snow fall 🌨️",
    73: "Moderate snow fall ❄️",
    75: "Heavy snow fall ❄️",
    80: "Slight rain showers 🌦️",
    81: "Moderate rain showers 🌧️",
    82: "Violent rain showers ⛈️",
    95: "Thunderstorm ⚡",
    96: "Thunderstorm with slight hail ⛈️",
    99: "Thunderstorm with heavy hail ⛈️"
}

def get_weather(location: str) -> str:
    """Get real-time weather for any city worldwide using Open-Meteo (100% Free, no API key needed)."""
    try:
        # Step 1: Geocode location name to lat/lon
        geo_url = "https://geocoding-api.open-meteo.com/v1/search"
        geo_res = httpx.get(geo_url, params={"name": location, "count": 1, "language": "en", "format": "json"}, timeout=6.0)
        geo_data = geo_res.json()
        
        if not geo_data.get("results"):
            return f"Could not find coordinates for location: '{location}'"
        
        loc_info = geo_data["results"][0]
        lat = loc_info["latitude"]
        lon = loc_info["longitude"]
        city_name = loc_info.get("name", location)
        country = loc_info.get("country", "")

        # Step 2: Fetch current weather
        weather_url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": ["temperature_2m", "relative_humidity_2m", "apparent_temperature", "weather_code", "wind_speed_10m"],
            "timezone": "auto"
        }
        w_res = httpx.get(weather_url, params=params, timeout=6.0)
        w_data = w_res.json()

        current = w_data.get("current", {})
        temp = current.get("temperature_2m", "N/A")
        feels_like = current.get("apparent_temperature", "N/A")
        humidity = current.get("relative_humidity_2m", "N/A")
        wind = current.get("wind_speed_10m", "N/A")
        code = current.get("weather_code", 0)
        condition = WEATHER_CODES.get(code, "Clear")

        return f"Weather for **{city_name}, {country}**:\n- Condition: {condition}\n- Temperature: {temp}°C (Feels like {feels_like}°C)\n- Humidity: {humidity}%\n- Wind Speed: {wind} km/h"

    except Exception as e:
        return f"Error retrieving weather for {location}: {str(e)}"
