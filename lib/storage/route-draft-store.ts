import { ROUTE_DRAFT_STORAGE_KEY } from "@/lib/shared/constants";
import type { LatLngLiteral, WaypointInput } from "@/lib/shared/types";

export interface RouteDraftSnapshot {
  origin: WaypointInput;
  destination: WaypointInput;
}

export const DEFAULT_ROUTE_DRAFT: RouteDraftSnapshot = {
  origin: { address: "Washington Square Park, New York, NY" },
  destination: { address: "Lincoln Center, New York, NY" },
};

export function buildRouteDraftSnapshot(
  origin: WaypointInput,
  destination: WaypointInput,
): RouteDraftSnapshot {
  return {
    origin: normalizeWaypoint(origin, DEFAULT_ROUTE_DRAFT.origin.address),
    destination: normalizeWaypoint(destination, DEFAULT_ROUTE_DRAFT.destination.address),
  };
}

export function loadRouteDraftSnapshot(): RouteDraftSnapshot | null {
  if (typeof window === "undefined") {
    return null;
  }

  try {
    const raw = window.localStorage.getItem(ROUTE_DRAFT_STORAGE_KEY);
    if (!raw) {
      return null;
    }

    const parsed = JSON.parse(raw) as Partial<RouteDraftSnapshot> | null;
    const origin = parsed?.origin;
    const destination = parsed?.destination;

    if (!origin || !destination) {
      return null;
    }

    return {
      origin: normalizeWaypoint(origin, ""),
      destination: normalizeWaypoint(destination, ""),
    };
  } catch {
    return null;
  }
}

export function saveRouteDraftSnapshot(snapshot: RouteDraftSnapshot) {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(
    ROUTE_DRAFT_STORAGE_KEY,
    JSON.stringify(buildRouteDraftSnapshot(snapshot.origin, snapshot.destination)),
  );
}

export function clearRouteDraftSnapshot() {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.removeItem(ROUTE_DRAFT_STORAGE_KEY);
}

function normalizeWaypoint(
  value: Partial<WaypointInput> | null | undefined,
  fallbackAddress: string,
): WaypointInput {
  const address = value?.address?.trim() ?? "";
  const location = normalizeLocation(value?.location);

  return {
    address: address || fallbackAddress,
    ...(location ? { location } : {}),
  };
}

function normalizeLocation(location: Partial<LatLngLiteral> | null | undefined): LatLngLiteral | undefined {
  if (location?.lat == null || location?.lng == null) {
    return undefined;
  }

  if (!Number.isFinite(location.lat) || !Number.isFinite(location.lng)) {
    return undefined;
  }

  return {
    lat: location.lat,
    lng: location.lng,
  };
}
