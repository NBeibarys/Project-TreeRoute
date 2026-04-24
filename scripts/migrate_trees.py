"""Load 2015 NYC tree census CSV into PostGIS.

Usage:
    python scripts/migrate_trees.py

Env overrides:
    DB_URL   postgresql://postgres:dev@localhost:5432/treeroute
"""
from __future__ import annotations

import asyncio
import csv
import os
from pathlib import Path

import asyncpg

DB_URL = os.getenv("DB_URL", "postgresql://postgres:dev@localhost:5432/treeroute")
CSV_PATH = Path(__file__).resolve().parents[1] / "data" / "2015_tree_census.csv"

DDL = """
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS trees (
    id          SERIAL PRIMARY KEY,
    species     TEXT NOT NULL,
    area_name   TEXT NOT NULL,
    geom        GEOMETRY(Point, 4326) NOT NULL
);

CREATE INDEX IF NOT EXISTS trees_geom_idx ON trees USING GIST (geom);
"""


async def main() -> None:
    conn = await asyncpg.connect(DB_URL)
    try:
        await conn.execute(DDL)

        existing = await conn.fetchval("SELECT COUNT(*) FROM trees")
        if existing > 0:
            print(f"Already {existing} rows — skipping import. Truncate to re-run.")
            return

        print(f"Loading {CSV_PATH} ...")
        batch: list[tuple[str, str, float, float]] = []
        skipped = 0

        with CSV_PATH.open("r", encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                try:
                    lat = float(row["latitude"])
                    lng = float(row["longitude"])
                    if not lat or not lng:
                        skipped += 1
                        continue
                    species = (row.get("spc_common") or "tree").strip().lower()
                    area = (row.get("nta_name") or "NYC").strip()
                    batch.append((species, area, lat, lng))
                except (ValueError, KeyError):
                    skipped += 1
                    continue

                if len(batch) >= 10_000:
                    await _insert(conn, batch)
                    batch.clear()

        if batch:
            await _insert(conn, batch)

        total = await conn.fetchval("SELECT COUNT(*) FROM trees")
        print(f"Inserted {total} trees. Skipped {skipped} rows.")
    finally:
        await conn.close()


async def _insert(conn: asyncpg.Connection, rows: list[tuple[str, str, float, float]]) -> None:
    await conn.executemany(
        "INSERT INTO trees (species, area_name, geom) VALUES ($1, $2, ST_SetSRID(ST_MakePoint($4, $3), 4326))",
        rows,
    )


if __name__ == "__main__":
    asyncio.run(main())
