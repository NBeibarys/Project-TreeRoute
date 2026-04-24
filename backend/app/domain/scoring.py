from __future__ import annotations

import math
from collections import Counter
from datetime import datetime

from app.domain.geometry import (
    clamp,
    decode_polyline,
    exposure_level_from_score,
    round_value,
    sample_route_points,
)
from app.domain.tree_data import TreeRecord, find_trees_for_points
from app.schemas.models import (
    ExposureLevel,
    GoogleRoute,
    LatLngLiteral,
    PollenSignal,
    RouteCandidate,
    RouteHotspot,
    RouteScoreBreakdown,
    RouteSignals,
    UserProfile,
    WeatherSignal,
)

TREE_EXPOSURE_RADIUS_METERS = 20
DEFAULT_BURDEN = 18.0
ROUTE_SAMPLE_SPACING_METERS = 20  # tighter spacing → no gaps in 20m buffer
MIN_ROUTE_SAMPLES = 10
MAX_ROUTE_SAMPLES = 80

SENSITIVITY_MULTIPLIERS = {
    "low": 0.88,
    "medium": 1.0,
    "high": 1.22,
}

SPECIES_SEASON_FACTOR = {
    "oak": [0.0, 0.0, 0.3, 1.0, 0.7, 0.1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    "birch": [0.0, 0.1, 0.8, 1.0, 0.2, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    "maple": [0.0, 0.1, 1.0, 0.6, 0.1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    "london plane": [0.0, 0.0, 0.2, 0.8, 1.0, 0.4, 0.1, 0.0, 0.0, 0.0, 0.0, 0.0],
    "plane tree": [0.0, 0.0, 0.2, 0.8, 1.0, 0.4, 0.1, 0.0, 0.0, 0.0, 0.0, 0.0],
    "honey locust": [0.0, 0.0, 0.0, 0.2, 0.9, 1.0, 0.3, 0.0, 0.0, 0.0, 0.0, 0.0],
    "locust": [0.0, 0.0, 0.0, 0.2, 0.9, 1.0, 0.3, 0.0, 0.0, 0.0, 0.0, 0.0],
    "elm": [0.0, 0.1, 1.0, 0.7, 0.1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    "pine": [0.0, 0.0, 0.2, 0.8, 0.6, 0.2, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    "cedar": [0.1, 0.2, 0.3, 0.2, 0.1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.2, 0.3],
    "mulberry": [0.0, 0.0, 0.1, 0.8, 1.0, 0.4, 0.1, 0.0, 0.0, 0.0, 0.0, 0.0],
    "ash": [0.0, 0.0, 0.3, 0.9, 0.5, 0.1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    "poplar": [0.0, 0.1, 0.7, 1.0, 0.4, 0.1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    "tree": [0.1, 0.2, 0.5, 0.8, 0.9, 0.8, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1],
}

SPECIES_ALLERGENIC_SCORE: dict[str, float] = {
    "oak": 9.0,
    "birch": 8.0,
    "cedar": 8.0,
    "mulberry": 8.0,
    "juniper": 8.0,
    "maple": 7.0,
    "elm": 7.0,
    "pine": 7.0,
    "ash": 7.0,
    "poplar": 6.0,
    "london plane": 6.0,
    "plane tree": 6.0,
    "honey locust": 5.0,
    "locust": 5.0,
    "willow": 5.0,
    "linden": 3.0,
    "ginkgo": 2.0,
    "tree": 5.0,
}
_DEFAULT_ALLERGENIC_SCORE = 4.0
_TRIGGER_MATCH_FACTOR = 1.6
_NON_TRIGGER_FACTOR = 0.6


async def score_routes(
    routes: list[GoogleRoute],
    profile: UserProfile,
    weather: WeatherSignal,
    pollen: PollenSignal,
    current_month: int | None = None,
    route_signals: list[RouteSignals] | None = None,
):
    month = _normalize_month(current_month)
    scored = []
    for index, route in enumerate(routes):
        result = await score_single_route(
            route,
            index,
            profile,
            route_signals[index].weather if route_signals and index < len(route_signals) else weather,
            route_signals[index].pollen if route_signals and index < len(route_signals) else pollen,
            month,
        )
        scored.append(result)
    return sorted(scored, key=lambda entry: entry["candidate"].exposureScore)


async def score_single_route(
    route: GoogleRoute,
    index: int,
    profile: UserProfile,
    weather: WeatherSignal,
    pollen: PollenSignal,
    month: int,
):
    points = decode_polyline(route.polyline)
    sample_count = _get_sample_count(route.distanceMeters)
    sampled = sample_route_points(points, sample_count)

    sensitivity = SENSITIVITY_MULTIPLIERS[profile.sensitivity]
    tree_matches = profile.triggers if profile.knowsTreeTriggers else []
    general_avoidance = (not profile.knowsTreeTriggers) or (not tree_matches)

    route_time_boost = clamp(route.durationMin / 36, 0.7, 1.25)
    pollen_factor = _get_pollen_factor(pollen)
    weather_boost = _get_weather_boost(weather)

    aggregate_burden = 0.0
    peak_burden = 0.0
    dominant_area = "NYC corridor"
    dominant_risk = 0.0
    hotspots: list[RouteHotspot] = []

    trees_per_point = await find_trees_for_points(sampled, TREE_EXPOSURE_RADIUS_METERS)

    for i, (point, trees) in enumerate(zip(sampled, trees_per_point)):
        burden, area_name = _compute_burden(trees, tree_matches, general_avoidance, month)

        aggregate_burden += burden
        peak_burden = max(peak_burden, burden)

        if burden >= dominant_risk:
            dominant_risk = burden
            dominant_area = area_name

        hotspots.append(RouteHotspot(
            lat=point.lat,
            lng=point.lng,
            label=f"{area_name} hotspot {i + 1}",
            risk=round_value(burden, 0),
        ))

    normalized_burden = aggregate_burden / len(sampled) if sampled else DEFAULT_BURDEN
    tree_exposure = normalized_burden * 0.28
    peak_tree_exposure = peak_burden * 0.12
    route_time_penalty = route_time_boost * 3
    tree_part = tree_exposure + peak_tree_exposure

    score = clamp(
        (tree_part * pollen_factor + route_time_penalty) * sensitivity * weather_boost,
        8,
        98,
    )

    exposure_level = exposure_level_from_score(score)
    rounded = round_value(score, 0)

    candidate = RouteCandidate(
        id=route.id,
        label=f"Route {chr(65 + index)}",
        polyline=route.polyline,
        durationMin=route.durationMin,
        distanceMeters=route.distanceMeters,
        exposureScore=rounded,
        exposureLevel=exposure_level,
        explanation="",
        rationale=_build_rationale(exposure_level, profile, dominant_area, weather, pollen),
        hotspots=sorted(hotspots, key=lambda h: h.risk, reverse=True)[:3],
        scoreBreakdown=RouteScoreBreakdown(
            treeExposure=round_value(tree_exposure, 1),
            peakTreeExposure=round_value(peak_tree_exposure, 1),
            routeTimePenalty=round_value(route_time_penalty, 1),
            pollenFactor=round_value(pollen_factor, 2),
            weatherFactor=round_value(weather_boost, 2),
            sensitivityFactor=round_value(sensitivity, 2),
            treePollenIndex=round_value(pollen.treeIndex, 1),
            windSpeedMph=round_value(weather.windSpeedMph, 1),
            finalScore=rounded,
        ),
    )

    return {
        "candidate": candidate,
        "dominant_area": dominant_area,
        "dominant_level": exposure_level,
    }


# ── internals ────────────────────────────────────────────────────────────────

def _normalize_month(current_month: int | None) -> int:
    if current_month is None:
        return datetime.now().month - 1
    return current_month % 12


def _get_sample_count(distance_meters: float) -> int:
    return int(clamp(
        math.floor(distance_meters / ROUTE_SAMPLE_SPACING_METERS + 0.5) + 1,
        MIN_ROUTE_SAMPLES,
        MAX_ROUTE_SAMPLES,
    ))


def _compute_burden(
    trees: list[TreeRecord],
    triggers: list[str],
    general_avoidance: bool,
    month: int,
) -> tuple[float, str]:
    if not trees:
        return DEFAULT_BURDEN, "NYC corridor"

    burden = sum(
        _tree_contribution(tree, triggers, general_avoidance, month)
        for tree in trees
    )
    area_name = Counter(t.area_name for t in trees).most_common(1)[0][0]
    return burden, area_name


def _tree_contribution(
    tree: TreeRecord,
    triggers: list[str],
    general_avoidance: bool,
    month: int,
) -> float:
    base = _allergenic_score(tree.species)
    seasonal = _seasonal_factor(tree.species, month)
    if general_avoidance:
        trigger_factor = 1.0
    elif _is_trigger(tree.species, triggers):
        trigger_factor = _TRIGGER_MATCH_FACTOR
    else:
        trigger_factor = _NON_TRIGGER_FACTOR
    return base * seasonal * trigger_factor


def _allergenic_score(species: str) -> float:
    s = species.lower()
    for key, score in SPECIES_ALLERGENIC_SCORE.items():
        if key in s or s in key:
            return score
    return _DEFAULT_ALLERGENIC_SCORE


def _seasonal_factor(species: str, month: int) -> float:
    s = species.lower()
    for key, factors in SPECIES_SEASON_FACTOR.items():
        if key in s or s in key:
            return factors[month]
    return SPECIES_SEASON_FACTOR["tree"][month]


def _is_trigger(species: str, triggers: list[str]) -> bool:
    s = species.lower()
    return any(t.lower() in s or s in t.lower() for t in triggers)


def _dominant_area(trees: list[TreeRecord]) -> str:
    return Counter(t.area_name for t in trees).most_common(1)[0][0]


def _get_pollen_factor(pollen: PollenSignal) -> float:
    index = pollen.treeIndex + pollen.grassIndex * 0.12 + pollen.weedIndex * 0.08
    return clamp(1 + index * 0.083, 1.0, 1.5)


def _get_weather_boost(weather: WeatherSignal) -> float:
    wind_factor = 1 + weather.windSpeedMph / 55
    humidity_factor = 1 - clamp((weather.humidity - 40) / 220, 0, 0.22)
    temp_factor = 1.05 if weather.temperatureF >= 75 else 0.95 if weather.temperatureF <= 45 else 1.0
    return clamp(wind_factor * humidity_factor * temp_factor, 0.86, 1.34)


def _build_rationale(
    level: ExposureLevel,
    profile: UserProfile,
    area_name: str,
    weather: WeatherSignal,
    pollen: PollenSignal,
) -> list[str]:
    lines = [f"{area_name} has elevated street-tree density relative to nearby blocks."]

    if profile.knowsTreeTriggers and profile.triggers:
        lines.append(f"Route ranked against your triggers: {', '.join(profile.triggers[:3])}.")
    else:
        lines.append("No triggers selected — route minimizes overall tree contact.")

    if pollen.treeIndex >= 4 or weather.windSpeedMph >= 12:
        lines.append(
            f"Tree pollen elevated, wind ~{round_value(weather.windSpeedMph, 0)} mph — spread risk higher on exposed blocks."
        )
    elif level == "low":
        lines.append("Route trades time for meaningfully lower tree-contact exposure.")
    else:
        lines.append("Route passes closer to denser canopy pockets.")

    return lines
