from __future__ import annotations

import math
from datetime import datetime

from app.domain.geometry import clamp, decode_polyline, exposure_level_from_score, round_value, sample_route_points
from app.domain.tree_grid import lookup_tree_cells_in_radius
from app.schemas.models import ExposureLevel, GoogleRoute, PollenSignal, RouteCandidate, RouteHotspot, TreeGridCell, UserProfile, WeatherSignal

TREE_EXPOSURE_RADIUS_METERS = 20
DEFAULT_BURDEN = 18

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
    "honey locust": [0.0, 0.0, 0.0, 0.2, 0.9, 1.0, 0.3, 0.0, 0.0, 0.0, 0.0, 0.0],
    "elm": [0.0, 0.1, 1.0, 0.7, 0.1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    "tree": [0.1, 0.2, 0.5, 0.8, 0.9, 0.8, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1],
}

TRIGGER_ALIASES = {
    "tree": ["tree", "trees"],
    "oak": ["oak", "oaks"],
    "birch": ["birch"],
    "maple": ["maple"],
    "london plane": ["london plane", "plane"],
    "honey locust": ["honey locust", "locust"],
    "elm": ["elm"],
}


def score_routes(
    routes: list[GoogleRoute],
    profile: UserProfile,
    weather: WeatherSignal,
    pollen: PollenSignal,
    current_month: int | None = None,
):
    month = normalize_month_index(current_month)
    scored = [
        score_single_route(route, index, profile, weather, pollen, month)
        for index, route in enumerate(routes)
    ]
    return sorted(scored, key=lambda entry: entry["candidate"].exposureScore)


def score_single_route(
    route: GoogleRoute,
    index: int,
    profile: UserProfile,
    weather: WeatherSignal,
    pollen: PollenSignal,
    month: int,
):
    points = decode_polyline(route.polyline)
    sample_count = int(clamp(math.floor(route.distanceMeters / 120 + 0.5), 10, 40))
    sampled_points = sample_route_points(points, sample_count)

    sensitivity = SENSITIVITY_MULTIPLIERS[profile.sensitivity]
    tree_matches = profile.triggers if profile.knowsTreeTriggers else []
    general_avoidance_mode = (not profile.knowsTreeTriggers) or (not tree_matches)
    route_time_boost = clamp(route.durationMin / 36, 0.7, 1.25)
    pollen_factor = get_tree_pollen_factor(pollen)
    weather_boost = get_weather_boost(weather)

    aggregate_burden = 0.0
    peak_burden = 0.0
    dominant_area = "NYC corridor"
    dominant_risk = 0.0
    hotspots: list[RouteHotspot] = []

    for point_index, point in enumerate(sampled_points):
        cells = lookup_tree_cells_in_radius(point, TREE_EXPOSURE_RADIUS_METERS)

        burden: float
        area_name = "NYC corridor"

        if not cells:
            burden = DEFAULT_BURDEN
        else:
            merged = merge_cells(cells)
            area_name = merged["area_name"]
            seasonal_weights = apply_seasonality(merged["species_weights"], month)
            species_boost = get_species_match_boost(
                tree_matches,
                seasonal_weights,
                merged["top_species"],
                general_avoidance_mode,
            )
            burden = merged["canopy_score"] * species_boost

        aggregate_burden += burden
        peak_burden = max(peak_burden, burden)

        if burden >= dominant_risk:
            dominant_risk = burden
            dominant_area = area_name

        hotspots.append(
            RouteHotspot(
                lat=point.lat,
                lng=point.lng,
                label=f"{area_name} hotspot {point_index + 1}",
                risk=round_value(burden, 0),
            )
        )

    normalized_burden = aggregate_burden / len(sampled_points) if sampled_points else DEFAULT_BURDEN
    tree_part = normalized_burden * 0.28 + peak_burden * 0.12
    score = clamp(
        (tree_part * pollen_factor + route_time_boost * 3) * sensitivity * weather_boost,
        8,
        98,
    )

    exposure_level = exposure_level_from_score(score)
    candidate = RouteCandidate(
        id=route.id,
        label=f"Route {chr(65 + index)}",
        polyline=route.polyline,
        durationMin=route.durationMin,
        distanceMeters=route.distanceMeters,
        exposureScore=round_value(score, 0),
        exposureLevel=exposure_level,
        explanation="",
        rationale=build_rationale(exposure_level, profile, dominant_area, weather, pollen),
        hotspots=sorted(hotspots, key=lambda item: item.risk, reverse=True)[:3],
    )

    return {
        "candidate": candidate,
        "dominant_area": dominant_area,
        "dominant_level": exposure_level,
    }


def normalize_month_index(current_month: int | None):
    if current_month is None:
        return datetime.now().month - 1

    return current_month % 12


def merge_cells(cells: list[TreeGridCell]):
    if len(cells) == 1:
        cell = cells[0]
        return {
            "canopy_score": cell.canopyScore,
            "species_weights": dict(cell.speciesWeights),
            "top_species": list(cell.topSpecies),
            "area_name": cell.areaName,
        }

    canopy_score = sum(cell.canopyScore for cell in cells) / len(cells)

    all_species = {
        species
        for cell in cells
        for species in cell.speciesWeights.keys()
    }
    species_weights: dict[str, float] = {}
    for species in all_species:
        average_weight = sum(cell.speciesWeights.get(species, 0.0) for cell in cells) / len(cells)
        if average_weight > 0:
            species_weights[species] = float(f"{average_weight:.2f}")

    top_species = [
        species
        for species, _weight in sorted(
            species_weights.items(),
            key=lambda item: item[1],
            reverse=True,
        )[:4]
    ]

    densest_cell = max(cells, key=lambda cell: cell.canopyScore)
    return {
        "canopy_score": canopy_score,
        "species_weights": species_weights,
        "top_species": top_species,
        "area_name": densest_cell.areaName,
    }


def apply_seasonality(species_weights: dict[str, float], month: int):
    seasonal_weights: dict[str, float] = {}

    for species, weight in species_weights.items():
        factors = SPECIES_SEASON_FACTOR.get(species, SPECIES_SEASON_FACTOR["tree"])
        seasonal_weights[species] = weight * factors[month]

    return seasonal_weights


def get_tree_pollen_factor(pollen: PollenSignal):
    index = pollen.treeIndex + pollen.grassIndex * 0.12 + pollen.weedIndex * 0.08
    return clamp(1 + index * 0.083, 1.0, 1.5)


def get_weather_boost(weather: WeatherSignal):
    wind_factor = 1 + weather.windSpeedMph / 55
    humidity_factor = 1 - clamp((weather.humidity - 40) / 220, 0, 0.22)
    temperature_factor = 1.05 if weather.temperatureF >= 75 else 0.95 if weather.temperatureF <= 45 else 1
    return clamp(wind_factor * humidity_factor * temperature_factor, 0.86, 1.34)


def get_species_match_boost(
    triggers: list[str],
    species_weights: dict[str, float],
    top_species: list[str],
    general_avoidance_mode: bool,
):
    if general_avoidance_mode:
        total_weight = sum(species_weights.values())
        return clamp(0.95 + total_weight * 0.55, 0.95, 1.55)

    matched_weight = 0.0
    for species, weight in species_weights.items():
        is_direct_trigger = species in triggers
        is_alias_match = any(
            any(alias in species for alias in TRIGGER_ALIASES.get(trigger, []))
            for trigger in triggers
        )
        matched_weight += weight if (is_direct_trigger or is_alias_match) else weight * 0.45

    top_species_boost = 0.3 if any(
        any(trigger.lower() in species.lower() for trigger in triggers)
        for species in top_species
    ) else 0.0

    return clamp(0.9 + matched_weight + top_species_boost, 0.8, 2.1)


def build_rationale(
    level: ExposureLevel,
    profile: UserProfile,
    area_name: str,
    weather: WeatherSignal,
    pollen: PollenSignal,
):
    lines = [f"{area_name} has elevated street-tree density relative to nearby blocks."]

    if profile.knowsTreeTriggers and profile.triggers:
        lines.append(f"This route is ranked against your selected tree triggers: {', '.join(profile.triggers[:3])}.")
    else:
        lines.append("No tree species were selected, so this route minimizes overall contact with trees.")

    if pollen.treeIndex >= 4 or weather.windSpeedMph >= 12:
        lines.append(
            f"Tree pollen is elevated and wind is around {round_value(weather.windSpeedMph, 0)} mph, so spread risk is higher on exposed blocks."
        )
    elif level == "low":
        lines.append("This route trades a bit of time for meaningfully lower tree-contact exposure.")
    else:
        lines.append("This option keeps you closer to denser canopy pockets for more of the walk.")

    return lines
