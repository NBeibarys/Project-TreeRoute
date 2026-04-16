from __future__ import annotations

import csv
import json
import math
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

from app.domain.scoring import TRIGGER_ALIASES

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUTPUT_PATH = REPO_ROOT / "data" / "generated" / "tree-grid.generated.json"


def main():
    if len(sys.argv) < 2:
        print("Usage: python backend/scripts/data/build_tree_grid.py <street-tree-census.csv> [output.json]", file=sys.stderr)
        sys.exit(1)

    input_path = Path(sys.argv[1]).resolve()
    output_path = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else DEFAULT_OUTPUT_PATH

    rows = read_csv(input_path)
    lat_key = find_header(rows["headers"], ["latitude", "lat"])
    lng_key = find_header(rows["headers"], ["longitude", "lng", "lon"])
    species_key = find_header(rows["headers"], ["spc_common", "species", "species_name"])
    area_key = find_header(rows["headers"], ["nta_name", "boroname", "zip_city"])

    if not lat_key or not lng_key or not species_key:
        print("Could not find latitude, longitude, and species columns in the CSV.", file=sys.stderr)
        sys.exit(1)

    points = []
    for record in rows["records"]:
        try:
            lat = float(record.get(lat_key, ""))
            lng = float(record.get(lng_key, ""))
        except ValueError:
            continue

        points.append(
            {
                "lat": lat,
                "lng": lng,
                "species": record.get(species_key, "unknown"),
                "area_name": record.get(area_key, "NYC canopy corridor") if area_key else "NYC canopy corridor",
            }
        )

    if not points:
        print("No valid rows found in the CSV.", file=sys.stderr)
        sys.exit(1)

    origin = {
        "lat": min(point["lat"] for point in points),
        "lng": min(point["lng"] for point in points),
    }
    lat_step = 0.00018
    lng_step = 0.00024

    buckets: dict[str, dict] = {}
    for point in points:
        lat_index = math.floor((point["lat"] - origin["lat"]) / lat_step)
        lng_index = math.floor((point["lng"] - origin["lng"]) / lng_step)
        key = f"{lat_index}:{lng_index}"
        bucket = buckets.setdefault(
            key,
            {
                "center_lat_sum": 0.0,
                "center_lng_sum": 0.0,
                "count": 0,
                "area_counts": defaultdict(int),
                "species_counts": defaultdict(int),
            },
        )

        bucket["center_lat_sum"] += point["lat"]
        bucket["center_lng_sum"] += point["lng"]
        bucket["count"] += 1
        bucket["area_counts"][point["area_name"]] += 1
        bucket["species_counts"][map_species_to_trigger(point["species"])] += 1

    max_count = max(bucket["count"] for bucket in buckets.values())
    cells = []

    for key, bucket in buckets.items():
        ordered_species = sorted(bucket["species_counts"].items(), key=lambda item: item[1], reverse=True)[:4]
        species_weights = {
            species: round(count / bucket["count"], 2)
            for species, count in ordered_species
        }

        cells.append(
            {
                "key": key,
                "center": {
                    "lat": round(bucket["center_lat_sum"] / bucket["count"], 6),
                    "lng": round(bucket["center_lng_sum"] / bucket["count"], 6),
                },
                "areaName": get_top_key(bucket["area_counts"]),
                "density": round(bucket["count"] / max_count, 2),
                "canopyScore": round((bucket["count"] / max_count) * 80),
                "topSpecies": list(species_weights.keys()),
                "speciesWeights": species_weights,
            }
        )

    tree_grid = {
        "version": date.today().isoformat(),
        "origin": origin,
        "latStep": lat_step,
        "lngStep": lng_step,
        "cellSizeMeters": 1100,
        "cells": cells,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(tree_grid, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(cells)} cells to {output_path}")


def read_csv(input_path: Path):
    with input_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        records = [dict(row) for row in reader]
        return {
            "headers": list(reader.fieldnames or []),
            "records": records,
        }


def find_header(headers: list[str], candidates: list[str]):
    lowered = {header.lower(): header for header in headers}
    for candidate in candidates:
        if candidate in lowered:
            return lowered[candidate]
    return None


def get_top_key(values: dict[str, int]):
    return sorted(values.items(), key=lambda item: item[1], reverse=True)[0][0] if values else "NYC canopy corridor"


def map_species_to_trigger(species: str):
    normalized = species.lower()
    for trigger, aliases in TRIGGER_ALIASES.items():
        if any(alias in normalized for alias in aliases):
            return trigger
    return "tree"


if __name__ == "__main__":
    main()
