import { postFastApiJson } from "@/lib/fastapi-client";
import type { RouteAnalysisRequest, RouteAnalysisResponse } from "@/lib/types";

export async function requestRouteAnalysis(
  request: RouteAnalysisRequest,
): Promise<RouteAnalysisResponse> {
  return postFastApiJson<RouteAnalysisResponse>("/route-analysis", request);
}
