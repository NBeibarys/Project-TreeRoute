from __future__ import annotations

import os

import httpx

from app.schemas.models import LatLngLiteral, PollenSignal

DEFAULT_POLLEN = PollenSignal(
    treeIndex=3,
    grassIndex=1,
    weedIndex=1,
    summary="Live pollen unavailable; using tree-grid-weighted fallback.",
)


def get_pollen_api_key():
    return os.getenv("GOOGLE_POLLEN_API_KEY") or os.getenv("GOOGLE_MAPS_API_KEY") or ""


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
