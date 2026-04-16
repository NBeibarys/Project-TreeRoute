from __future__ import annotations

import math
import os

import httpx

from app.domain.geometry import distance_meters, encode_polyline, midpoint, round_value
from app.schemas.models import GoogleRoute, LatLngLiteral, ResolvedWaypoint

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


def get_maps_api_key():
    return os.getenv("GOOGLE_MAPS_API_KEY") or os.getenv("NEXT_PUBLIC_GOOGLE_MAPS_API_KEY") or ""


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
    routes: list[GoogleRoute] = []
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
