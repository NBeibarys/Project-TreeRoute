from __future__ import annotations

import math

from app.schemas.models import ExposureLevel, LatLngLiteral


def clamp(value: float, minimum: float, maximum: float):
    return min(maximum, max(minimum, value))


def round_value(value: float, precision: int = 1):
    factor = 10**precision
    return round(value * factor) / factor


def midpoint(points: list[LatLngLiteral]):
    if not points:
        return LatLngLiteral(lat=40.758, lng=-73.9855)

    return LatLngLiteral(
        lat=sum(point.lat for point in points) / len(points),
        lng=sum(point.lng for point in points) / len(points),
    )


def distance_meters(a: LatLngLiteral, b: LatLngLiteral):
    earth_radius = 6_371_000
    lat1 = math.radians(a.lat)
    lat2 = math.radians(b.lat)
    delta_lat = math.radians(b.lat - a.lat)
    delta_lng = math.radians(b.lng - a.lng)

    haversine = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lng / 2) ** 2
    )
    arc = 2 * math.atan2(math.sqrt(haversine), math.sqrt(1 - haversine))
    return earth_radius * arc


def sample_route_points(points: list[LatLngLiteral], samples: int = 12):
    if len(points) <= samples:
        return points

    bucket = (len(points) - 1) / (samples - 1)
    return [points[round(index * bucket)] for index in range(samples)]


def exposure_level_from_score(score: float) -> ExposureLevel:
    if score < 32:
        return "low"
    if score < 62:
        return "moderate"
    return "high"


def decode_polyline(encoded: str) -> list[LatLngLiteral]:
    index = 0
    lat = 0
    lng = 0
    coordinates: list[LatLngLiteral] = []

    while index < len(encoded):
        result = 0
        shift = 0
        while True:
            byte = ord(encoded[index]) - 63
            index += 1
            result |= (byte & 0x1F) << shift
            shift += 5
            if byte < 0x20:
                break

        delta_lat = ~(result >> 1) if result & 1 else result >> 1
        lat += delta_lat

        result = 0
        shift = 0
        while True:
            byte = ord(encoded[index]) - 63
            index += 1
            result |= (byte & 0x1F) << shift
            shift += 5
            if byte < 0x20:
                break

        delta_lng = ~(result >> 1) if result & 1 else result >> 1
        lng += delta_lng
        coordinates.append(LatLngLiteral(lat=lat / 1e5, lng=lng / 1e5))

    return coordinates


def encode_polyline(points: list[LatLngLiteral]) -> str:
    last_lat = 0
    last_lng = 0
    encoded_parts: list[str] = []

    for point in points:
        lat = round(point.lat * 1e5)
        lng = round(point.lng * 1e5)
        encoded_parts.append(encode_signed_number(lat - last_lat))
        encoded_parts.append(encode_signed_number(lng - last_lng))
        last_lat = lat
        last_lng = lng

    return "".join(encoded_parts)


def encode_signed_number(value: int):
    shifted = ~(value << 1) if value < 0 else value << 1
    output = ""

    while shifted >= 0x20:
        output += chr((0x20 | (shifted & 0x1F)) + 63)
        shifted >>= 5

    output += chr(shifted + 63)
    return output
