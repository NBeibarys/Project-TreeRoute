from __future__ import annotations

import json
import os
from typing import Any

from app.schemas.models import PollenSignal, RouteCandidate, RoutingMode, UserProfile, WeatherSignal


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
