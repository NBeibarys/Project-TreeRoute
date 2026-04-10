from __future__ import annotations

import json
import math
import os
from typing import Any

import httpx

from .geometry import distance_meters, encode_polyline, midpoint, round_value
from .models import GoogleRoute, LatLngLiteral, PollenSignal, ResolvedWaypoint, RouteCandidate, RoutingMode, UserProfile, WeatherSignal

MAPS_BASE_URL = "https://maps.googleapis.com"
ROUTES_BASE_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"

DEMO_LOCATIONS: dict[str, LatLngLiteral] = {
    "washington square park": LatLngLiteral(lat=40.7308, lng=-73.9973),
    "lincoln center": LatLngLiteral(lat=40.7725, lng=-73.9835),
    "times square": LatLngLiteral(lat=40.7580, lng=-73.9855),
    "grand central terminal": LatLngLiteral(lat=40.7527, lng=-73.9772),
    "bryant park": LatLngLiteral(lat=40.7536, lng=-73.9832),
    "union square": LatLngLiteral(lat=40.7359, lng=-73.9911),
    "columbus circle": LatLngLiteral(lat=40.7681, lng=-73.9819),
}

DEFAULT_WEATHER = WeatherSignal(
    description="Weather fallback active; using calm spring conditions.",
    windSpeedMph=8,
    humidity=54,
    temperatureF=61,
)

DEFAULT_POLLEN = PollenSignal(
    treeIndex=3,
    grassIndex=1,
    weedIndex=1,
    summary="Live pollen unavailable; using tree-grid-weighted fallback.",
)


def get_maps_api_key():
    return os.getenv("GOOGLE_MAPS_API_KEY") or os.getenv("NEXT_PUBLIC_GOOGLE_MAPS_API_KEY") or ""


def get_weather_api_key():
    return os.getenv("GOOGLE_WEATHER_API_KEY") or os.getenv("GOOGLE_MAPS_API_KEY") or ""


def get_pollen_api_key():
    return os.getenv("GOOGLE_POLLEN_API_KEY") or os.getenv("GOOGLE_MAPS_API_KEY") or ""


async def geocode_address(address: str) -> ResolvedWaypoint:
    api_key = get_maps_api_key()
    demo_location = resolve_demo_location(address)

    if not api_key:
        if demo_location:
            return demo_location
        raise ValueError("Missing GOOGLE_MAPS_API_KEY for geocoding.")

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(
            f"{MAPS_BASE_URL}/maps/api/geocode/json",
            params={
                "address": address,
                "components": "country:US|administrative_area:NY",
                "key": api_key,
            },
        )

    if response.status_code != 200:
        raise ValueError(f"Geocoding failed with status {response.status_code}")

    payload = response.json()
    result = (payload.get("results") or [None])[0]
    location = ((result or {}).get("geometry") or {}).get("location") or {}

    if not result or location.get("lat") is None or location.get("lng") is None:
        if demo_location:
            return demo_location
        raise ValueError(f"Unable to geocode address: {address}")

    return ResolvedWaypoint(
        address=result.get("formatted_address") or address,
        location=LatLngLiteral(lat=float(location["lat"]), lng=float(location["lng"])),
    )


def resolve_demo_location(address: str) -> ResolvedWaypoint | None:
    normalized = address.strip().lower()
    coordinate_match = normalized.split(",")

    if len(coordinate_match) == 2:
        try:
            return ResolvedWaypoint(
                address=address,
                location=LatLngLiteral(
                    lat=float(coordinate_match[0].strip()),
                    lng=float(coordinate_match[1].strip()),
                ),
            )
        except ValueError:
            pass

    for key, point in DEMO_LOCATIONS.items():
        if key in normalized:
            return ResolvedWaypoint(address=address, location=point)

    return None


async def compute_alternative_walking_routes(
    origin: LatLngLiteral,
    destination: LatLngLiteral,
) -> list[GoogleRoute]:
    api_key = get_maps_api_key()
    if not api_key:
        raise ValueError("Missing GOOGLE_MAPS_API_KEY for route computation.")

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            ROUTES_BASE_URL,
            headers={
                "Content-Type": "application/json",
                "X-Goog-Api-Key": api_key,
                "X-Goog-FieldMask": "routes.distanceMeters,routes.duration,routes.polyline.encodedPolyline",
            },
            json={
                "origin": {"location": {"latLng": {"latitude": origin.lat, "longitude": origin.lng}}},
                "destination": {"location": {"latLng": {"latitude": destination.lat, "longitude": destination.lng}}},
                "travelMode": "WALK",
                "computeAlternativeRoutes": True,
                "polylineQuality": "HIGH_QUALITY",
                "languageCode": "en-US",
                "units": "IMPERIAL",
            },
        )

    if response.status_code != 200:
        raise ValueError(f"Routes API failed with status {response.status_code}")

    payload = response.json()
    routes = []
    for index, route in enumerate(payload.get("routes") or []):
        routes.append(
            GoogleRoute(
                id=f"live-{index + 1}",
                polyline=((route.get("polyline") or {}).get("encodedPolyline") or ""),
                durationMin=round_value(parse_duration_minutes(route.get("duration")), 0),
                distanceMeters=float(route.get("distanceMeters") or 0),
            )
        )

    if not routes or all(not route.polyline for route in routes):
        raise ValueError("Routes API returned no usable routes.")

    return routes[:3]


def build_fallback_routes(origin: LatLngLiteral, destination: LatLngLiteral) -> list[GoogleRoute]:
    direct_distance = distance_meters(origin, destination)
    baseline_minutes = max(10, round(direct_distance / 72))
    center = midpoint([origin, destination])
    delta_lat = destination.lat - origin.lat
    delta_lng = destination.lng - origin.lng
    perpendicular = normalize_vector(LatLngLiteral(lat=-delta_lng, lng=delta_lat))

    offsets = [0, 0.0065, -0.0054]
    routes: list[GoogleRoute] = []

    for index, offset in enumerate(offsets):
        via_point = LatLngLiteral(
            lat=center.lat + perpendicular.lat * offset,
            lng=center.lng + perpendicular.lng * offset,
        )

        if index == 0:
            points = [origin, destination]
        else:
            first_mid = midpoint([origin, via_point])
            second_mid = midpoint([via_point, destination])
            points = [
                origin,
                LatLngLiteral(lat=first_mid.lat + offset * 0.3, lng=first_mid.lng + offset * 0.14),
                via_point,
                LatLngLiteral(lat=second_mid.lat - offset * 0.18, lng=second_mid.lng - offset * 0.1),
                destination,
            ]

        distance_multiplier = 1 if index == 0 else 1 + abs(offset) * 12
        routes.append(
            GoogleRoute(
                id=f"fallback-{index + 1}",
                polyline=encode_polyline(points),
                durationMin=baseline_minutes + index * 3 + round(distance_multiplier * 2),
                distanceMeters=round(direct_distance * distance_multiplier),
            )
        )

    return routes


def parse_duration_minutes(duration: str | None):
    if not duration:
        return 0

    try:
        seconds = float(duration.replace("s", ""))
    except ValueError:
        return 0

    return seconds / 60


def normalize_vector(point: LatLngLiteral):
    length = math.sqrt(point.lat**2 + point.lng**2)
    if not length:
        return LatLngLiteral(lat=0.5, lng=0.5)

    return LatLngLiteral(lat=point.lat / length, lng=point.lng / length)


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


async def get_pollen_signal(point: LatLngLiteral) -> PollenSignal:
    api_key = get_pollen_api_key()
    if not api_key:
        raise ValueError("Missing Google Pollen API key.")

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(
            "https://pollen.googleapis.com/v1/forecast:lookup",
            params={
                "key": api_key,
                "days": 1,
                "location.latitude": point.lat,
                "location.longitude": point.lng,
            },
        )

    if response.status_code != 200:
        raise ValueError(f"Pollen API failed with status {response.status_code}")

    payload = response.json()
    pollen_types = (((payload.get("dailyInfo") or [{}])[0]).get("pollenTypeInfo") or [])

    def lookup(code: str):
        for entry in pollen_types:
            if entry.get("code") == code:
                return float(((entry.get("indexInfo") or {}).get("value")) or 1)
        return 1.0

    tree_index = lookup("TREE")
    grass_index = lookup("GRASS")
    weed_index = lookup("WEED")
    max_index = max(tree_index, grass_index, weed_index)

    return PollenSignal(
        treeIndex=tree_index,
        grassIndex=grass_index,
        weedIndex=weed_index,
        summary=(
            "Pollen pressure is elevated today, so route shape matters."
            if max_index >= 4
            else "Pollen conditions are moderate enough that local tree density drives most of the risk."
        ),
    )


async def generate_grounded_copy(
    profile: UserProfile,
    routes: list[RouteCandidate],
    weather: WeatherSignal,
    pollen: PollenSignal,
    area_name: str,
    burden_level: str,
    routing_mode: RoutingMode,
):
    api_key = os.getenv("GOOGLE_AI_API_KEY") or ""
    if not api_key:
        return build_fallback_copy(profile, routes, weather, pollen, area_name, burden_level, routing_mode)

    try:
        from google import genai  # type: ignore

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=os.getenv("GEMINI_MODEL") or "gemini-2.5-flash",
            contents=json.dumps(
                {
                    "task": "Generate grounded route copy from the analysis payload below.",
                    "payload": {
                        "profile": profile.model_dump(),
                        "routes": [route.model_dump() for route in routes],
                        "weather": weather.model_dump(),
                        "pollen": pollen.model_dump(),
                        "areaName": area_name,
                        "burdenLevel": burden_level,
                        "routingMode": routing_mode,
                    },
                }
            ),
            config={
                "system_instruction": (
                    "You are a routing assistant. Always respond with a single valid JSON object only. "
                    "The JSON must have summary, civicSummary, and routeExplanations. "
                    "Keep each explanation under 45 words. Use only provided data."
                )
            },
        )
        text = getattr(response, "text", "") or ""
        parsed = json.loads(extract_json_object(text))
        return normalize_generated_copy(parsed, routes)
    except Exception:
        return build_fallback_copy(profile, routes, weather, pollen, area_name, burden_level, routing_mode)


def build_fallback_copy(
    profile: UserProfile,
    routes: list[RouteCandidate],
    weather: WeatherSignal,
    pollen: PollenSignal,
    area_name: str,
    burden_level: str,
    routing_mode: RoutingMode,
):
    best = routes[0] if routes else None
    target_label = ", ".join(profile.triggers) if routing_mode == "specific-tree-triggers" and profile.triggers else "overall street-tree contact"

    route_explanations: dict[str, Any] = {}
    for index, route in enumerate(routes):
        route_explanations[route.id] = {
            "explanation": (
                f"{route.label} is the safest tradeoff today because it avoids the densest tree pockets while keeping walking time realistic."
                if index == 0
                else f"{route.label} keeps you closer to denser tree-lined blocks, so its tree-contact burden is higher today."
            ),
            "rationale": route.rationale,
        }

    summary = (
        f"{best.label} is the recommended route because it lowers likely exposure to {target_label} while accounting for today's tree pollen and wind conditions."
        if best
        else "Route analysis complete."
    )

    return {
        "summary": summary,
        "civicSummary": (
            f"{area_name} shows why allergy burden is uneven across NYC: tree density, local pollen pressure, and wind make nearby blocks feel very different for residents trying to limit exposure."
        ),
        "routeExplanations": route_explanations,
    }


def extract_json_object(text: str):
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("Gemini response did not contain JSON.")
    return text[start : end + 1]


def normalize_generated_copy(payload: Any, routes: list[RouteCandidate]):
    if not isinstance(payload, dict):
        raise ValueError("Generated copy payload must be an object.")

    summary = payload.get("summary")
    civic_summary = payload.get("civicSummary")

    if not isinstance(summary, str) or not summary.strip():
        raise ValueError("Missing grounded copy summary.")

    if not isinstance(civic_summary, str) or not civic_summary.strip():
        raise ValueError("Missing grounded copy civic summary.")

    return {
        "summary": summary.strip(),
        "civicSummary": civic_summary.strip(),
        "routeExplanations": normalize_route_explanations(payload.get("routeExplanations"), routes),
    }


def normalize_route_explanations(payload: Any, routes: list[RouteCandidate]):
    route_ids = {route.id for route in routes}
    normalized: dict[str, dict[str, Any]] = {}

    if isinstance(payload, dict):
        for route_id, entry in payload.items():
            if not isinstance(route_id, str) or route_id not in route_ids:
                continue

            normalized_entry = normalize_route_explanation(entry)
            if normalized_entry:
                normalized[route_id] = normalized_entry

        return normalized

    if not isinstance(payload, list):
        return normalized

    for index, entry in enumerate(payload):
        if not isinstance(entry, dict):
            continue

        explicit_route_id = entry.get("routeId") or entry.get("route_id") or entry.get("id")
        route_id = explicit_route_id if isinstance(explicit_route_id, str) and explicit_route_id in route_ids else None

        if route_id is None and index < len(routes):
            route_id = routes[index].id

        if route_id is None:
            continue

        normalized_entry = normalize_route_explanation(entry)
        if normalized_entry:
            normalized[route_id] = normalized_entry

    return normalized


def normalize_route_explanation(payload: Any):
    if not isinstance(payload, dict):
        return None

    explanation = payload.get("explanation")
    rationale = payload.get("rationale")

    normalized_explanation = explanation.strip() if isinstance(explanation, str) else ""
    normalized_rationale = [
        item.strip()
        for item in rationale
        if isinstance(item, str) and item.strip()
    ] if isinstance(rationale, list) else []

    if not normalized_explanation and not normalized_rationale:
        return None

    return {
        "explanation": normalized_explanation,
        "rationale": normalized_rationale,
    }
