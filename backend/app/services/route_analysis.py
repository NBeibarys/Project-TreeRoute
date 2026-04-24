from __future__ import annotations

import asyncio

from app.domain.geometry import decode_polyline, round_value, sample_route_points
from app.domain.scoring import score_routes
from app.integrations.gemini import generate_grounded_copy
from app.integrations.maps import (
    build_fallback_routes,
    compute_alternative_walking_routes,
    geocode_address,
)
from app.integrations.pollen import (
    DEFAULT_POLLEN,
    get_pollen_signal,
)
from app.integrations.weather import (
    DEFAULT_WEATHER,
    get_weather_signal,
)
from app.schemas.models import (
    CivicInsight,
    GoogleRoute,
    PollenSignal,
    ResolvedWaypoint,
    RouteAnalysisRequest,
    RouteAnalysisResponse,
    RouteCandidate,
    RouteSignals,
    RoutingMode,
    WaypointInput,
    LatLngLiteral,
    WeatherSignal,
)


async def analyze_route_request(request: RouteAnalysisRequest) -> RouteAnalysisResponse:
    validate_request(request)

    origin = await resolve_waypoint(request.origin)
    destination = await resolve_waypoint(request.destination)
    fallback_mode: list[str] = []

    routes = await get_routes_with_fallback(origin.location, destination.location, fallback_mode)
    route_signals, weather, pollen = await build_route_signal_context(routes, fallback_mode)
    scored_routes = await score_routes(
        routes,
        request.profile,
        weather,
        pollen,
        route_signals=route_signals,
    )
    routing_mode: RoutingMode = (
        "specific-tree-triggers"
        if request.profile.knowsTreeTriggers and request.profile.triggers
        else "general-tree-avoidance"
    )

    top_area = scored_routes[0]["dominant_area"] if scored_routes else "Central Manhattan"
    top_level = scored_routes[0]["dominant_level"] if scored_routes else "moderate"
    copy = await generate_grounded_copy(
        profile=request.profile,
        routes=[entry["candidate"] for entry in scored_routes],
        weather=weather,
        pollen=pollen,
        area_name=top_area,
        burden_level=top_level,
        routing_mode=routing_mode,
    )

    enriched_routes = [
        apply_generated_copy(entry["candidate"], copy["routeExplanations"])
        for entry in scored_routes
    ]

    return RouteAnalysisResponse(
        originResolved=origin.address,
        destinationResolved=destination.address,
        originPoint=origin.location,
        destinationPoint=destination.location,
        summary=copy["summary"],
        routingMode=routing_mode,
        dataSources=[
            "Google Maps Geocoding API",
            "Google Routes API",
            "Google Pollen API",
            "Google Weather API",
            "Gemini via Google GenAI SDK",
            "NYC 2015 Street Tree Census",
        ],
        routes=enriched_routes,
        civicInsight=CivicInsight(
            areaName=top_area,
            treeBurdenLevel=top_level,
            summary=copy["civicSummary"],
        ),
        weather=weather,
        pollen=pollen,
        fallbackMode=fallback_mode,
    )


def validate_request(request: RouteAnalysisRequest):
    if not request.origin.address and not request.origin.location:
        raise ValueError("Origin is required.")

    if not request.destination.address and not request.destination.location:
        raise ValueError("Destination is required.")

    if request.profile.knowsTreeTriggers and not request.profile.triggers:
        raise ValueError("Choose at least one tree trigger or switch to general tree avoidance.")


async def resolve_waypoint(waypoint: WaypointInput):
    if waypoint.location:
        return ResolvedWaypoint(address=waypoint.address or "Selected point", location=waypoint.location)

    return await geocode_address(waypoint.address)


async def get_routes_with_fallback(
    origin: LatLngLiteral,
    destination: LatLngLiteral,
    fallback_mode: list[str],
):
    try:
        live_routes = await compute_alternative_walking_routes(origin, destination)
        if live_routes:
            return live_routes
    except Exception:
        fallback_mode.append("fallback-routes")

    return build_fallback_routes(origin, destination)


async def build_route_signal_context(
    routes: list[GoogleRoute],
    fallback_mode: list[str],
):
    if not routes:
        return [], DEFAULT_WEATHER, DEFAULT_POLLEN

    weather_cache: dict[str, asyncio.Task[WeatherSignal]] = {}
    pollen_cache: dict[str, asyncio.Task[PollenSignal]] = {}

    async def load_weather(point: LatLngLiteral):
        try:
            return await get_weather_signal(point)
        except Exception:
            append_fallback_mode(fallback_mode, "fallback-weather")
            return DEFAULT_WEATHER

    async def load_pollen(point: LatLngLiteral):
        try:
            return await get_pollen_signal(point)
        except Exception:
            append_fallback_mode(fallback_mode, "fallback-pollen")
            return DEFAULT_POLLEN

    async def get_cached_weather(point: LatLngLiteral):
        key = build_point_cache_key(point)
        task = weather_cache.get(key)
        if task is None:
            task = asyncio.create_task(load_weather(point))
            weather_cache[key] = task
        return await task

    async def get_cached_pollen(point: LatLngLiteral):
        key = build_point_cache_key(point)
        task = pollen_cache.get(key)
        if task is None:
            task = asyncio.create_task(load_pollen(point))
            pollen_cache[key] = task
        return await task

    async def build_signals_for_route(route: GoogleRoute):
        signal_points = build_route_signal_points(route)
        if not signal_points:
            append_fallback_mode(fallback_mode, "fallback-weather")
            append_fallback_mode(fallback_mode, "fallback-pollen")
            return RouteSignals(weather=DEFAULT_WEATHER, pollen=DEFAULT_POLLEN)

        weather_signals, pollen_signals = await asyncio.gather(
            asyncio.gather(*(get_cached_weather(point) for point in signal_points)),
            asyncio.gather(*(get_cached_pollen(point) for point in signal_points)),
        )
        return RouteSignals(
            weather=merge_weather_signals(list(weather_signals)),
            pollen=merge_pollen_signals(list(pollen_signals)),
        )

    route_signals = list(await asyncio.gather(*(build_signals_for_route(route) for route in routes)))
    return (
        route_signals,
        merge_weather_signals([signal.weather for signal in route_signals]),
        merge_pollen_signals([signal.pollen for signal in route_signals]),
    )


def build_route_signal_points(route: GoogleRoute):
    points = decode_polyline(route.polyline)
    return sample_route_points(points, 3)


def build_point_cache_key(point: LatLngLiteral):
    return f"{point.lat:.5f}:{point.lng:.5f}"


def merge_weather_signals(signals: list[WeatherSignal]):
    if not signals:
        return DEFAULT_WEATHER

    average_wind = sum(signal.windSpeedMph for signal in signals) / len(signals)
    average_humidity = sum(signal.humidity for signal in signals) / len(signals)
    average_temperature = sum(signal.temperatureF for signal in signals) / len(signals)
    unique_descriptions = {signal.description for signal in signals if signal.description}

    return WeatherSignal(
        description=(
            unique_descriptions.pop()
            if len(unique_descriptions) == 1
            else "Weather averaged across route corridor sample points."
        ),
        windSpeedMph=round_value(average_wind, 1),
        humidity=round_value(average_humidity, 0),
        temperatureF=round_value(average_temperature, 0),
    )


def merge_pollen_signals(signals: list[PollenSignal]):
    if not signals:
        return DEFAULT_POLLEN

    average_tree_index = sum(signal.treeIndex for signal in signals) / len(signals)
    average_grass_index = sum(signal.grassIndex for signal in signals) / len(signals)
    average_weed_index = sum(signal.weedIndex for signal in signals) / len(signals)
    max_index = max(average_tree_index, average_grass_index, average_weed_index)

    return PollenSignal(
        treeIndex=round_value(average_tree_index, 1),
        grassIndex=round_value(average_grass_index, 1),
        weedIndex=round_value(average_weed_index, 1),
        summary=(
            "Pollen pressure is elevated across this route corridor."
            if max_index >= 4
            else "Pollen conditions are moderate across this route corridor."
        ),
    )


def append_fallback_mode(fallback_mode: list[str], value: str):
    if value not in fallback_mode:
        fallback_mode.append(value)


def apply_generated_copy(candidate: RouteCandidate, generated: dict[str, dict]):
    if not isinstance(generated, dict):
        return candidate

    copy = generated.get(candidate.id)
    if not isinstance(copy, dict):
        return candidate

    rationale = copy.get("rationale") if isinstance(copy.get("rationale"), list) else candidate.rationale
    explanation = copy.get("explanation") if isinstance(copy.get("explanation"), str) else candidate.explanation

    return RouteCandidate(
        **{
            **candidate.model_dump(),
            "explanation": explanation,
            "rationale": rationale,
        }
    )
