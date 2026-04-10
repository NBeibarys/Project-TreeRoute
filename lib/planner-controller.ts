"use client";

import {
  startTransition,
  useDeferredValue,
  useEffect,
  useMemo,
  useState,
  type FormEvent,
} from "react";
import { useRouter } from "next/navigation";

import {
  clearProfileDraft,
  loadProfileDraft,
  normalizeProfileDraft,
} from "@/lib/profile-store";
import {
  clearRouteDraftSnapshot,
  DEFAULT_ROUTE_DRAFT,
  loadRouteDraftSnapshot,
} from "@/lib/route-draft-store";
import { hasCompletedRegistration } from "@/lib/registration-status";
import { requestRouteAnalysis } from "@/lib/route-analysis-client";
import { speakRouteSummary } from "@/lib/route-summary-speech";
import type { RouteAnalysisResponse, UserProfile, WaypointInput } from "@/lib/types";

const DEFAULT_STATUS =
  "Build a route to see the lowest expected pollen exposure.";

const ANALYZING_STATUS =
  "Analyzing walking alternatives against tree density, pollen, weather, and wind...";

const ANALYZE_ERROR =
  "We could not build routes right now. Check your API keys and try again.";

const ANALYZE_FAILED_STATUS = "Unable to finish the live route analysis.";

const VOICE_FILLED_STATUS =
  "Route filled from voice - press Find Safe Route to analyze.";

export function usePlannerController() {
  const router = useRouter();
  const [profile, setProfile] = useState<UserProfile>(normalizeProfileDraft(loadProfileDraft()));
  const [origin, setOrigin] = useState<WaypointInput>(DEFAULT_ROUTE_DRAFT.origin);
  const [destination, setDestination] = useState<WaypointInput>(DEFAULT_ROUTE_DRAFT.destination);
  const [analysis, setAnalysis] = useState<RouteAnalysisResponse | null>(null);
  const [selectedRouteId, setSelectedRouteId] = useState("");
  const [mapsReady, setMapsReady] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [statusLine, setStatusLine] = useState(DEFAULT_STATUS);
  const [ready, setReady] = useState(false);

  const visibleAnalysis = useDeferredValue(analysis);
  const selectedRoute = useMemo(
    () =>
      visibleAnalysis?.routes.find((route) => route.id === selectedRouteId) ??
      visibleAnalysis?.routes[0] ??
      null,
    [visibleAnalysis, selectedRouteId],
  );

  useEffect(() => {
    const storedProfile = loadProfileDraft();

    if (!hasCompletedRegistration(storedProfile)) {
      router.replace("/register");
      return;
    }

    setProfile(normalizeProfileDraft(storedProfile));

    const draft = loadRouteDraftSnapshot();
    if (draft) {
      setOrigin(draft.origin.address ? draft.origin : DEFAULT_ROUTE_DRAFT.origin);
      setDestination(draft.destination.address ? draft.destination : DEFAULT_ROUTE_DRAFT.destination);
    }

    setReady(true);
  }, [router]);

  async function handleAnalyze(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError("");
    setStatusLine(ANALYZING_STATUS);

    try {
      const response = await requestRouteAnalysis({
        origin,
        destination,
        profile,
      });

      startTransition(() => {
        setAnalysis(response);
        setSelectedRouteId(response.routes[0]?.id ?? "");
        setStatusLine(response.summary);
      });

      speakRouteSummary(response);
      clearRouteDraftSnapshot();
    } catch (caughtError) {
      const message = caughtError instanceof Error ? caughtError.message : ANALYZE_ERROR;
      setError(message);
      setStatusLine(ANALYZE_FAILED_STATUS);
    } finally {
      setLoading(false);
    }
  }

  function handleResetRegistration() {
    clearProfileDraft();
    router.push("/register");
  }

  function handleOriginChange(nextOrigin: WaypointInput) {
    setOrigin(nextOrigin);
  }

  function handleDestinationChange(nextDestination: WaypointInput) {
    setDestination(nextDestination);
  }

  function handleVoiceResult(voiceOrigin: string, voiceDestination: string) {
    if (voiceOrigin) {
      setOrigin({ address: voiceOrigin });
    }

    if (voiceDestination) {
      setDestination({ address: voiceDestination });
    }

    if (voiceOrigin || voiceDestination) {
      setStatusLine(VOICE_FILLED_STATUS);
    }
  }

  return {
    analysis: visibleAnalysis,
    destination,
    error,
    handleAnalyze,
    handleDestinationChange,
    handleOriginChange,
    handleResetRegistration,
    handleVoiceResult,
    loading,
    mapsReady,
    origin,
    profile,
    ready,
    selectedRoute,
    selectedRouteId,
    setMapsReady,
    setSelectedRouteId,
    statusLine,
  };
}
