import type { ExposureLevel, Sensitivity } from "@/shared/contracts/types";

export const PROFILE_STORAGE_KEY = "pollen-safe-profile";
export const ROUTE_DRAFT_STORAGE_KEY = "treeroute-route-draft";

export const ALLERGY_TRIGGER_OPTIONS = [
  "oak",
  "birch",
  "maple",
  "london plane",
  "honey locust",
  "elm",
] as const;

export const SENSITIVITY_MULTIPLIERS: Record<Sensitivity, number> = {
  low: 0.88,
  medium: 1,
  high: 1.22,
};

export const EXPOSURE_LABELS: Record<ExposureLevel, string> = {
  low: "Low exposure",
  moderate: "Moderate exposure",
  high: "High exposure",
};

// Seasonal pollen activity by species — index 0=Jan … 11=Dec
// Values are relative activity factors (0.0 = dormant, 1.0 = peak).
export const SPECIES_SEASON_FACTOR: Record<string, number[]> = {
  oak:            [0.0, 0.0, 0.3, 1.0, 0.7, 0.1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
  birch:          [0.0, 0.1, 0.8, 1.0, 0.2, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
  maple:          [0.0, 0.1, 1.0, 0.6, 0.1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
  "london plane": [0.0, 0.0, 0.2, 0.8, 1.0, 0.4, 0.1, 0.0, 0.0, 0.0, 0.0, 0.0],
  "honey locust": [0.0, 0.0, 0.0, 0.2, 0.9, 1.0, 0.3, 0.0, 0.0, 0.0, 0.0, 0.0],
  elm:            [0.0, 0.1, 1.0, 0.7, 0.1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
  tree:           [0.1, 0.2, 0.5, 0.8, 0.9, 0.8, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1],
};

export const TRIGGER_ALIASES: Record<string, string[]> = {
  tree: ["tree", "trees"],
  oak: ["oak", "oaks"],
  birch: ["birch"],
  maple: ["maple"],
  "london plane": ["london plane", "plane"],
  "honey locust": ["honey locust", "locust"],
  elm: ["elm"],
};
