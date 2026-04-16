from __future__ import annotations

import os

import httpx

from app.schemas.models import LatLngLiteral, WeatherSignal

DEFAULT_WEATHER = WeatherSignal(
    description="Weather fallback active; using calm spring conditions.",
    windSpeedMph=8,
    humidity=54,
    temperatureF=61,
)


def get_weather_api_key():
    return os.getenv("GOOGLE_WEATHER_API_KEY") or os.getenv("GOOGLE_MAPS_API_KEY") or ""


async def get_weather_signal(point: LatLngLiteral) -> WeatherSignal:
    api_key = get_weather_api_key()
    if not api_key:
        raise ValueError("Missing Google Weather API key.")

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(
            "https://weather.googleapis.com/v1/currentConditions:lookup",
            params={
                "key": api_key,
                "unitsSystem": "IMPERIAL",
                "location.latitude": point.lat,
                "location.longitude": point.lng,
            },
        )

    if response.status_code != 200:
        raise ValueError(f"Weather API failed with status {response.status_code}")

    payload = response.json()
    wind = (payload.get("wind") or {}).get("speed") or {}
    wind_value = float(wind.get("value") or 7)
    wind_unit = wind.get("unit") or "MILES_PER_HOUR"
    wind_speed_mph = wind_value * 0.621371 if wind_unit == "KILOMETERS_PER_HOUR" else wind_value

    return WeatherSignal(
        description=(((payload.get("weatherCondition") or {}).get("description") or {}).get("text") or "Current neighborhood conditions loaded"),
        windSpeedMph=wind_speed_mph,
        humidity=float(payload.get("relativeHumidity") or 58),
        temperatureF=float((payload.get("temperature") or {}).get("degrees") or 63),
    )
