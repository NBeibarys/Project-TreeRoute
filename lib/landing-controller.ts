"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import {
  loadRouteDraftSnapshot,
  saveRouteDraftSnapshot,
} from "@/lib/route-draft-store";
import {
  hasCompletedRegistration,
  loadStoredProfileSnapshot,
} from "@/lib/registration-status";
import type { WaypointInput } from "@/lib/types";

const EMPTY_WAYPOINT: WaypointInput = { address: "" };

export function useLandingController() {
  const router = useRouter();
  const [registered, setRegistered] = useState(false);
  const [origin, setOrigin] = useState<WaypointInput>(EMPTY_WAYPOINT);
  const [destination, setDestination] = useState<WaypointInput>(EMPTY_WAYPOINT);
  const [mapsReady, setMapsReady] = useState(false);

  useEffect(() => {
    setRegistered(hasCompletedRegistration(loadStoredProfileSnapshot()));

    const savedDraft = loadRouteDraftSnapshot();
    if (!savedDraft) {
      return;
    }

    setOrigin(savedDraft.origin);
    setDestination(savedDraft.destination);
  }, []);

  function handlePrimaryNavigation() {
    router.push(registered ? "/planner" : "/register");
  }

  function handleRouteIntent() {
    saveRouteDraftSnapshot({ origin, destination });
    handlePrimaryNavigation();
  }

  function handleVoiceResult(voiceOrigin: string, voiceDestination: string) {
    if (voiceOrigin) {
      setOrigin({ address: voiceOrigin });
    }

    if (voiceDestination) {
      setDestination({ address: voiceDestination });
    }
  }

  return {
    destination,
    handlePrimaryNavigation,
    handleRouteIntent,
    handleVoiceResult,
    mapsReady,
    origin,
    registered,
    setDestination,
    setMapsReady,
    setOrigin,
  };
}
