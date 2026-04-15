import { postFastApiJson } from "@/lib/api/fastapi-client";
import type { RouteAnalysisRequest, RouteAnalysisResponse } from "@/lib/shared/types";

export async function requestRouteAnalysis(
  request: RouteAnalysisRequest,
): Promise<RouteAnalysisResponse> {
  return postFastApiJson<RouteAnalysisResponse>("/route-analysis", request);
}
