"""
Ambon Alert - MCP server
A small MCP server that lets Claude get the weather for any city.
Uses Open-Meteo (free, no API key needed).

Needs: Python 3.10+ and `pip install mcp` (version 2 or newer).
"""

import json
import urllib.parse
import urllib.request

from mcp.server.mcpserver import MCPServer

# 1. Make the server and give it a name
mcp = MCPServer("ambon-alert")

GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"

# Weather codes -> simple words
WEATHER_WORDS = {
    0: "Clear sky", 1: "Mostly clear", 2: "Partly cloudy", 3: "Cloudy",
    45: "Foggy", 48: "Foggy",
    51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle",
    61: "Light rain", 63: "Rain", 65: "Heavy rain",
    80: "Rain showers", 81: "Rain showers", 82: "Strong rain showers",
    95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Thunderstorm with hail",
}


def get_json(url: str, params: dict) -> dict:
    """Call a web API and return the JSON answer."""
    full_url = url + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(full_url, timeout=10) as response:
        return json.load(response)


def find_city(city: str) -> dict | None:
    """Turn a city name into latitude and longitude."""
    data = get_json(GEO_URL, {"name": city, "count": 1})
    results = data.get("results")
    return results[0] if results else None


# 2. A "tool" = one action Claude can do
@mcp.tool()
def get_weather(city: str) -> str:
    """Get the current weather for a city. Example: "Mandaluyong"."""
    place = find_city(city)
    if place is None:
        return f"Sorry, I can't find the city '{city}'."

    data = get_json(WEATHER_URL, {
        "latitude": place["latitude"],
        "longitude": place["longitude"],
        "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
        "timezone": "auto",
    })
    now = data["current"]
    sky = WEATHER_WORDS.get(now["weather_code"], "Unknown")

    return (
        f"Weather in {place['name']}, {place.get('country', '')}:\n"
        f"- Sky: {sky}\n"
        f"- Temperature: {now['temperature_2m']} °C\n"
        f"- Humidity: {now['relative_humidity_2m']}%\n"
        f"- Wind: {now['wind_speed_10m']} km/h"
    )


@mcp.tool()
def will_it_rain(city: str) -> str:
    """Check the chance of rain today in a city."""
    place = find_city(city)
    if place is None:
        return f"Sorry, I can't find the city '{city}'."

    data = get_json(WEATHER_URL, {
        "latitude": place["latitude"],
        "longitude": place["longitude"],
        "daily": "precipitation_probability_max",
        "timezone": "auto",
        "forecast_days": 1,
    })
    chance = data["daily"]["precipitation_probability_max"][0]

    tip = "Bring an umbrella! ☔" if chance >= 50 else "No umbrella needed. 😎"
    return f"Chance of rain today in {place['name']}: {chance}%. {tip}"


@mcp.tool()
def get_forecast(city: str, days: int = 7) -> str:
    """Get the weather forecast for the next days (1 to 7) in a city."""
    days = max(1, min(days, 7))
    place = find_city(city)
    if place is None:
        return f"Sorry, I can't find the city '{city}'."

    data = get_json(WEATHER_URL, {
        "latitude": place["latitude"],
        "longitude": place["longitude"],
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
        "timezone": "auto",
        "forecast_days": days,
    })
    daily = data["daily"]

    lines = [f"{days}-day forecast for {place['name']}:"]
    for i, date in enumerate(daily["time"]):
        sky = WEATHER_WORDS.get(daily["weather_code"][i], "Unknown")
        low = daily["temperature_2m_min"][i]
        high = daily["temperature_2m_max"][i]
        rain = daily["precipitation_probability_max"][i]
        lines.append(f"- {date}: {sky}, {low}–{high} °C, rain {rain}%")
    return "\n".join(lines)


# 3. Start the server
if __name__ == "__main__":
    mcp.run()
