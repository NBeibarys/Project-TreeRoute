import type { ExposureLevel, Sensitivity } from "@/lib/shared/types";

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

export const TRIGGER_ALIASES: Record<string, string[]> = {
  tree: ["tree", "trees"],
  oak: ["oak", "oaks"],
  birch: ["birch"],
  maple: ["maple"],
  "london plane": ["london plane", "plane"],
  "honey locust": ["honey locust", "locust"],
  elm: ["elm"],
};
