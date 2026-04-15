from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path

from .models import LatLngLiteral, TreeGridCell, TreeGridData

TREE_GRID_PATH = Path(__file__).resolve().parents[2] / "data" / "tree-grid.sample.json"


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
