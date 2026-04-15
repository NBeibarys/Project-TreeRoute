import { buildRouteSummarySpeechText } from "@/lib/planner/route-summary-speech";
import { requestRouteAnalysis } from "@/lib/planner/route-analysis-client";
import type { RouteAnalysisResponse } from "@/lib/shared/types";

const baseResponse: RouteAnalysisResponse = {
  originResolved: "Start",
  destinationResolved: "End",
  originPoint: { lat: 40.74, lng: -73.98 },
  destinationPoint: { lat: 40.76, lng: -73.99 },
  summary: "Route A is safest today.",
  routingMode: "general-tree-avoidance",
  dataSources: ["test"],
  routes: [
    {
      id: "route-a",
      label: "Route A",
      polyline: "abc",
      durationMin: 14,
      distanceMeters: 1200,
      exposureScore: 18,
      exposureLevel: "low",
      explanation: "It avoids denser tree pockets.",
      rationale: ["Lower canopy burden"],
      hotspots: [],
    },
  ],
  civicInsight: {
    areaName: "Midtown",
    treeBurdenLevel: "low",
    summary: "Lower tree burden nearby.",
  },
  weather: {
    description: "Clear",
    windSpeedMph: 7,
    humidity: 55,
    temperatureF: 62,
  },
  pollen: {
    treeIndex: 3,
    grassIndex: 1,
    weedIndex: 1,
    summary: "Moderate tree pollen.",
  },
  fallbackMode: [],
};

describe("planner logic", () => {
  const originalBaseUrl = process.env.NEXT_PUBLIC_FASTAPI_BASE_URL;

  beforeEach(() => {
    process.env.NEXT_PUBLIC_FASTAPI_BASE_URL = "http://localhost:8000";
  });

  afterEach(() => {
    vi.restoreAllMocks();

    if (originalBaseUrl === undefined) {
      delete process.env.NEXT_PUBLIC_FASTAPI_BASE_URL;
    } else {
      process.env.NEXT_PUBLIC_FASTAPI_BASE_URL = originalBaseUrl;
    }
  });

  it("builds speech text from the top-ranked route", () => {
    const text = buildRouteSummarySpeechText(baseResponse);

    expect(text).toContain("Route A is safest today.");
    expect(text).toContain("The recommended route is Route A.");
    expect(text).toContain("score of 18");
  });

  it("returns an empty speech text when there are no routes", () => {
    const text = buildRouteSummarySpeechText({
      ...baseResponse,
      routes: [],
    });

    expect(text).toBe("");
  });

  it("returns parsed route analysis data from the API", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => baseResponse,
      }),
    );

    const response = await requestRouteAnalysis({
      origin: { address: "Start" },
      destination: { address: "End" },
      profile: {
        triggers: [],
        sensitivity: "medium",
        knowsTreeTriggers: false,
      },
    });

    expect(fetch).toHaveBeenCalledWith(
      "http://localhost:8000/route-analysis",
      expect.objectContaining({
        method: "POST",
      }),
    );
    expect(response.summary).toBe("Route A is safest today.");
  });

  it("throws a readable API error when the backend responds with failure", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        json: async () => ({ error: "Service unavailable" }),
      }),
    );

    await expect(
      requestRouteAnalysis({
        origin: { address: "Start" },
        destination: { address: "End" },
        profile: {
          triggers: [],
          sensitivity: "medium",
          knowsTreeTriggers: false,
        },
      }),
    ).rejects.toThrow("Service unavailable");
  });

  it("reads FastAPI detail errors without breaking the UI contract", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        json: async () => ({ detail: "Origin is required." }),
      }),
    );

    await expect(
      requestRouteAnalysis({
        origin: { address: "" },
        destination: { address: "End" },
        profile: {
          triggers: [],
          sensitivity: "medium",
          knowsTreeTriggers: false,
        },
      }),
    ).rejects.toThrow("Origin is required.");
  });
});
