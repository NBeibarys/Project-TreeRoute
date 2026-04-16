from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path

from app.domain.geometry import distance_meters
from app.schemas.models import LatLngLiteral, TreeGridCell, TreeGridData

TREE_GRID_PATH = Path(__file__).resolve().parents[3] / "data" / "sample" / "tree-grid.sample.json"


@lru_cache(maxsize=1)
def get_tree_grid() -> TreeGridData:
    with TREE_GRID_PATH.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return TreeGridData.model_validate(payload)


@lru_cache(maxsize=1)
def build_cell_lookup():
    return {cell.key: cell for cell in get_tree_grid().cells}


def get_grid_key(point: LatLngLiteral, grid: TreeGridData | None = None):
    selected_grid = grid or get_tree_grid()
    lat_index = math.floor((point.lat - selected_grid.origin.lat) / selected_grid.latStep)
    lng_index = math.floor((point.lng - selected_grid.origin.lng) / selected_grid.lngStep)
    return f"{lat_index}:{lng_index}"


def lookup_tree_cell(point: LatLngLiteral, grid: TreeGridData | None = None) -> TreeGridCell | None:
    selected_grid = grid or get_tree_grid()
    return build_cell_lookup().get(get_grid_key(point, selected_grid))


def lookup_tree_cells_in_radius(
    point: LatLngLiteral,
    radius_meters: float,
    grid: TreeGridData | None = None,
) -> list[TreeGridCell]:
    selected_grid = grid or get_tree_grid()
    lookup = build_cell_lookup()
    lat_index = math.floor((point.lat - selected_grid.origin.lat) / selected_grid.latStep)
    lng_index = math.floor((point.lng - selected_grid.origin.lng) / selected_grid.lngStep)

    lat_range = math.ceil(radius_meters / (selected_grid.latStep * 111_000)) + 1
    lng_range = math.ceil(radius_meters / (selected_grid.lngStep * 84_000)) + 1

    primary_key = f"{lat_index}:{lng_index}"
    results: list[TreeGridCell] = []

    for delta_lat in range(-lat_range, lat_range + 1):
        for delta_lng in range(-lng_range, lng_range + 1):
            key = f"{lat_index + delta_lat}:{lng_index + delta_lng}"
            cell = lookup.get(key)
            if cell is None:
                continue

            if key == primary_key or distance_meters(point, cell.center) <= radius_meters:
                results.append(cell)

    return results
