from __future__ import annotations

from .geometry import midpoint
from .models import CivicInsight, ResolvedWaypoint, RouteAnalysisRequest, RouteAnalysisResponse, RouteCandidate, RoutingMode
from .providers import (
    DEFAULT_POLLEN,
    DEFAULT_WEATHER,
    build_fallback_routes,
    compute_alternative_walking_routes,
    generate_grounded_copy,
    geocode_address,
    get_pollen_signal,
    get_weather_signal,
)
from .scoring import score_routes


async def analyze_route_request(request: RouteAnalysisRequest) -> RouteAnalysisResponse:
    validate_request(request)

    origin = await resolve_waypoint(request.origin)
    destination = await resolve_waypoint(request.destination)
    center_point = midpoint([origin.location, destination.location])
    fallback_mode: list[str] = []

    routes = await get_routes_with_fallback(origin.location, destination.location, fallback_mode)
    weather = await get_weather_with_fallback(center_point, fallback_mode)
    pollen = await get_pollen_with_fallback(center_point, fallback_mode)
    scored_routes = score_routes(routes, request.profile, weather, pollen)
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
            "Google Maps Routes API",
            "Google Maps JavaScript API",
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


async def resolve_waypoint(waypoint):
    if waypoint.location:
        return ResolvedWaypoint(address=waypoint.address or "Selected point", location=waypoint.location)

    return await geocode_address(waypoint.address)


async def get_routes_with_fallback(origin, destination, fallback_mode: list[str]):
    try:
        live_routes = await compute_alternative_walking_routes(origin, destination)
        if live_routes:
            return live_routes
    except Exception:
        fallback_mode.append("fallback-routes")

    return build_fallback_routes(origin, destination)


async def get_weather_with_fallback(point, fallback_mode: list[str]):
    try:
        return await get_weather_signal(point)
    except Exception:
        fallback_mode.append("fallback-weather")
        return DEFAULT_WEATHER


async def get_pollen_with_fallback(point, fallback_mode: list[str]):
    try:
        return await get_pollen_signal(point)
    except Exception:
        fallback_mode.append("fallback-pollen")
        return DEFAULT_POLLEN


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
