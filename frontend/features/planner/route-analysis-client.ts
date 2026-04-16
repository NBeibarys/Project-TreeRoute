import { postFastApiJson } from "@/shared/api/fastapi-client";
import type { RouteAnalysisRequest, RouteAnalysisResponse } from "@/shared/contracts/types";

export async function requestRouteAnalysis(
  request: RouteAnalysisRequest,
): Promise<RouteAnalysisResponse> {
  return postFastApiJson<RouteAnalysisResponse>("/route-analysis", request);
}
