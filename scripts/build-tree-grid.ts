import fs from "node:fs";
import path from "node:path";

import { TRIGGER_ALIASES } from "@/lib/shared/constants";
import type { TreeGridCell, TreeGridData } from "@/lib/shared/types";

const inputPath = process.argv[2];
const outputPath = process.argv[3] ?? "data/tree-grid.generated.json";

if (!inputPath) {
  console.error("Usage: npm run build-tree-grid -- <street-tree-census.csv> [output.json]");
  process.exit(1);
}

const csv = fs.readFileSync(path.resolve(inputPath), "utf8");
const rows = parseCsv(csv);

const latKey = rows.headers.find((header) => ["latitude", "lat"].includes(header.toLowerCase()));
const lngKey = rows.headers.find((header) => ["longitude", "lng", "lon"].includes(header.toLowerCase()));
const speciesKey = rows.headers.find((header) =>
  ["spc_common", "species", "species_name"].includes(header.toLowerCase()),
);
const areaKey = rows.headers.find((header) => ["nta_name", "boroname", "zip_city"].includes(header.toLowerCase()));

if (!latKey || !lngKey || !speciesKey) {
  console.error("Could not find latitude, longitude, and species columns in the CSV.");
  process.exit(1);
}

const points = rows.records
  .map((record) => ({
    lat: Number(record[latKey]),
    lng: Number(record[lngKey]),
    species: record[speciesKey] ?? "unknown",
    areaName: areaKey ? record[areaKey] ?? "NYC canopy corridor" : "NYC canopy corridor",
  }))
  .filter((record) => !Number.isNaN(record.lat) && !Number.isNaN(record.lng));

if (!points.length) {
  console.error("No valid rows found in the CSV.");
  process.exit(1);
}

const origin = {
  lat: Math.min(...points.map((point) => point.lat)),
  lng: Math.min(...points.map((point) => point.lng)),
};
// ~20 m resolution — fine enough for the 20 m pedestrian-exposure radius query.
// At NYC latitude: 0.00018 deg lat ≈ 20 m, 0.00024 deg lng ≈ 20 m.
const latStep = 0.00018;
const lngStep = 0.00024;

const buckets = new Map<
  string,
  {
    centerLatSum: number;
    centerLngSum: number;
    count: number;
    areaCounts: Map<string, number>;
    speciesCounts: Map<string, number>;
  }
>();

for (const point of points) {
  const latIndex = Math.floor((point.lat - origin.lat) / latStep);
  const lngIndex = Math.floor((point.lng - origin.lng) / lngStep);
  const key = `${latIndex}:${lngIndex}`;
  const bucket = buckets.get(key) ?? {
    centerLatSum: 0,
    centerLngSum: 0,
    count: 0,
    areaCounts: new Map<string, number>(),
    speciesCounts: new Map<string, number>(),
  };

  bucket.centerLatSum += point.lat;
  bucket.centerLngSum += point.lng;
  bucket.count += 1;
  bucket.areaCounts.set(point.areaName, (bucket.areaCounts.get(point.areaName) ?? 0) + 1);
  const trigger = mapSpeciesToTrigger(point.species);
  bucket.speciesCounts.set(trigger, (bucket.speciesCounts.get(trigger) ?? 0) + 1);
  buckets.set(key, bucket);
}

const maxCount = Math.max(...Array.from(buckets.values(), (bucket) => bucket.count));
const cells: TreeGridCell[] = Array.from(buckets.entries()).map(([key, bucket]) => {
  const speciesWeights = Object.fromEntries(
    Array.from(bucket.speciesCounts.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 4)
      .map(([species, count]) => [species, Number((count / bucket.count).toFixed(2))]),
  );

  return {
    key,
    center: {
      lat: Number((bucket.centerLatSum / bucket.count).toFixed(6)),
      lng: Number((bucket.centerLngSum / bucket.count).toFixed(6)),
    },
    areaName: getTopKey(bucket.areaCounts),
    density: Number((bucket.count / maxCount).toFixed(2)),
    canopyScore: Math.round((bucket.count / maxCount) * 80),
    topSpecies: Object.keys(speciesWeights),
    speciesWeights,
  };
});

const treeGrid: TreeGridData = {
  version: new Date().toISOString().slice(0, 10),
  origin,
  latStep,
  lngStep,
  cellSizeMeters: 1100,
  cells,
};

fs.writeFileSync(path.resolve(outputPath), `${JSON.stringify(treeGrid, null, 2)}\n`);
console.log(`Wrote ${cells.length} cells to ${outputPath}`);

function getTopKey(values: Map<string, number>) {
  return Array.from(values.entries()).sort((a, b) => b[1] - a[1])[0]?.[0] ?? "NYC canopy corridor";
}

function mapSpeciesToTrigger(species: string) {
  const normalized = species.toLowerCase();

  for (const [trigger, aliases] of Object.entries(TRIGGER_ALIASES) as Array<[string, string[]]>) {
    if (aliases.some((alias) => normalized.includes(alias))) {
      return trigger;
    }
  }

  return "tree";
}

function parseCsv(input: string) {
  const lines = input.split(/\r?\n/).filter(Boolean);
  const headers = splitCsvLine(lines[0] ?? "");
  const records = lines.slice(1).map((line) => {
    const values = splitCsvLine(line);
    return Object.fromEntries(headers.map((header, index) => [header, values[index] ?? ""]));
  });

  return { headers, records };
}

function splitCsvLine(line: string) {
  const fields: string[] = [];
  let current = "";
  let inQuotes = false;

  for (let index = 0; index < line.length; index += 1) {
    const character = line[index];

    if (character === '"' && line[index + 1] === '"') {
      current += '"';
      index += 1;
      continue;
    }

    if (character === '"') {
      inQuotes = !inQuotes;
      continue;
    }

    if (character === "," && !inQuotes) {
      fields.push(current);
      current = "";
      continue;
    }

    current += character;
  }

  fields.push(current);
  return fields;
}
