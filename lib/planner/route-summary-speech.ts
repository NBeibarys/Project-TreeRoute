import type { RouteAnalysisResponse } from "@/lib/shared/types";

export function speakRouteSummary(response: RouteAnalysisResponse) {
  if (typeof window === "undefined" || !window.speechSynthesis) {
    return;
  }

  const text = buildRouteSummarySpeechText(response);
  if (!text) {
    return;
  }

  window.speechSynthesis.cancel();

  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = "en-US";
  utterance.rate = 0.95;
  window.speechSynthesis.speak(utterance);
}

export function buildRouteSummarySpeechText(response: RouteAnalysisResponse) {
  const bestRoute = response.routes[0];
  if (!bestRoute) {
    return "";
  }

  return [
    response.summary,
    `The recommended route is ${bestRoute.label}.`,
    `Its exposure level is ${bestRoute.exposureLevel} with a score of ${bestRoute.exposureScore}.`,
    bestRoute.explanation,
  ].join(" ");
}
