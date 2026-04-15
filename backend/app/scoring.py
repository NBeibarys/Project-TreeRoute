from __future__ import annotations

from .geometry import clamp, decode_polyline, exposure_level_from_score, round_value, sample_route_points
from .models import GoogleRoute, PollenSignal, RouteCandidate, RouteHotspot, UserProfile, WeatherSignal
from .tree_grid import lookup_tree_cell

SENSITIVITY_MULTIPLIERS = {
    "low": 0.88,
    "medium": 1.0,
    "high": 1.22,
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
):
    scored = [
        score_single_route(route, index, profile, weather, pollen)
        for index, route in enumerate(routes)
    ]
    return sorted(scored, key=lambda entry: entry["candidate"].exposureScore)


def score_single_route(
    route: GoogleRoute,
    index: int,
    profile: UserProfile,
    weather: WeatherSignal,
    pollen: PollenSignal,
):
    points = decode_polyline(route.polyline)
    sampled_points = sample_route_points(points, 14)
    sensitivity = SENSITIVITY_MULTIPLIERS[profile.sensitivity]
    tree_matches = profile.triggers if profile.knowsTreeTriggers else []
    general_avoidance_mode = (not profile.knowsTreeTriggers) or (not tree_matches)
    route_time_boost = clamp(route.durationMin / 36, 0.7, 1.25)
    pollen_boost = get_tree_pollen_boost(pollen)
    weather_boost = get_weather_boost(weather)

    aggregate_burden = 0.0
    peak_burden = 0.0
    dominant_area = "NYC corridor"
    dominant_risk = 0.0
    hotspots: list[RouteHotspot] = []

    for point_index, point in enumerate(sampled_points):
        cell = lookup_tree_cell(point)
        if not cell:
            continue

        species_boost = get_species_match_boost(
            tree_matches,
            cell.speciesWeights,
            cell.topSpecies,
            general_avoidance_mode,
        )
        burden = cell.canopyScore * species_boost
        aggregate_burden += burden
        peak_burden = max(peak_burden, burden)

        if burden >= dominant_risk:
            dominant_risk = burden
            dominant_area = cell.areaName

        hotspots.append(
            RouteHotspot(
                lat=point.lat,
                lng=point.lng,
                label=f"{cell.areaName} hotspot {point_index + 1}",
                risk=round_value(burden, 0),
            )
        )

    normalized_burden = aggregate_burden / len(sampled_points) if sampled_points else 18
    score = clamp(
        (normalized_burden * 0.34 + peak_burden * 0.1 + pollen_boost * 5 + route_time_boost * 3)
        * sensitivity
        * weather_boost,
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


def get_tree_pollen_boost(pollen: PollenSignal):
    return clamp(pollen.treeIndex + pollen.grassIndex * 0.12 + pollen.weedIndex * 0.08, 1, 5.5)


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
    level: str,
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
