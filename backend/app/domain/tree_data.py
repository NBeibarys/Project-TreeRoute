from __future__ import annotations

import logging
import os
from dataclasses import dataclass

import asyncpg

from app.schemas.models import LatLngLiteral

logger = logging.getLogger(__name__)

DB_URL = os.getenv("DB_URL", "postgresql://postgres:dev@localhost:5432/treeroute")

_pool: asyncpg.Pool | None = None


@dataclass(frozen=True, slots=True)
class TreeRecord:
    lat: float
    lng: float
    species: str
    area_name: str


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(DB_URL, min_size=2, max_size=10)
        logger.info("PostGIS pool created → %s", DB_URL)
    return _pool


async def find_trees_in_radius(point: LatLngLiteral, radius_meters: float) -> list[TreeRecord]:
    pool = await get_pool()
    rows = await pool.fetch(
        """
        SELECT species, area_name,
               ST_Y(geom) AS lat, ST_X(geom) AS lng
        FROM   trees
        WHERE  ST_DWithin(
                   geom::geography,
                   ST_SetSRID(ST_MakePoint($2, $1), 4326)::geography,
                   $3
               )
        """,
        point.lat,
        point.lng,
        radius_meters,
    )
    return [
        TreeRecord(lat=r["lat"], lng=r["lng"], species=r["species"], area_name=r["area_name"])
        for r in rows
    ]


async def find_trees_for_points(
    points: list[LatLngLiteral], radius_meters: float
) -> list[list[TreeRecord]]:
    """Batch query — one list of TreeRecords per input point."""
    if not points:
        return []

    pool = await get_pool()
    lats = [p.lat for p in points]
    lngs = [p.lng for p in points]

    rows = await pool.fetch(
        """
        WITH pts AS (
            SELECT ordinality - 1 AS idx, lat, lng
            FROM unnest($1::float8[], $2::float8[])
                 WITH ORDINALITY AS t(lat, lng)
        )
        SELECT pts.idx,
               t.species,
               t.area_name,
               ST_Y(t.geom) AS tree_lat,
               ST_X(t.geom) AS tree_lng
        FROM   pts
        JOIN   trees t
          ON   ST_DWithin(
                   t.geom::geography,
                   ST_SetSRID(ST_MakePoint(pts.lng, pts.lat), 4326)::geography,
                   $3
               )
        ORDER BY pts.idx
        """,
        lats,
        lngs,
        radius_meters,
    )

    result: list[list[TreeRecord]] = [[] for _ in points]
    for r in rows:
        result[r["idx"]].append(
            TreeRecord(
                lat=r["tree_lat"],
                lng=r["tree_lng"],
                species=r["species"],
                area_name=r["area_name"],
            )
        )
    return result
