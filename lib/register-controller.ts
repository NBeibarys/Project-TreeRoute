"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { DEFAULT_ROUTE_DRAFT, loadRouteDraftSnapshot } from "@/lib/route-draft-store";
import {
  buildCompletedProfile,
  DEFAULT_PROFILE_DRAFT,
  loadProfileDraft,
  normalizeProfileDraft,
  saveProfileDraft,
  validateProfileDraft,
} from "@/lib/profile-store";
import type { Sensitivity, UserProfile } from "@/lib/types";

export function useRegisterController() {
  const router = useRouter();
  const [profile, setProfile] = useState<UserProfile>(() =>
    normalizeProfileDraft(loadProfileDraft() ?? DEFAULT_PROFILE_DRAFT),
  );
  const [error, setError] = useState("");
  const [routeSummary, setRouteSummary] = useState(DEFAULT_ROUTE_DRAFT);

  useEffect(() => {
    const savedDraft = loadRouteDraftSnapshot();
    if (savedDraft) {
      setRouteSummary(savedDraft);
    }
  }, []);

  function handleBack() {
    router.push("/");
  }

  function updateProfile(nextProfile: UserProfile) {
    setProfile({
      ...nextProfile,
      registrationComplete: false,
    });
    setError("");
  }

  function handleNameChange(value: string) {
    updateProfile({ ...profile, name: value });
  }

  function handleEmailChange(value: string) {
    updateProfile({ ...profile, email: value });
  }

  function handleSensitivityChange(value: Sensitivity) {
    updateProfile({ ...profile, sensitivity: value });
  }

  function handleKnowledgeChange(knowsTreeTriggers: boolean) {
    updateProfile({
      ...profile,
      knowsTreeTriggers,
      triggers: knowsTreeTriggers ? profile.triggers : [],
    });
  }

  function handleTriggerToggle(trigger: string) {
    const active = profile.triggers.includes(trigger);

    updateProfile({
      ...profile,
      triggers: active
        ? profile.triggers.filter((item) => item !== trigger)
        : [...profile.triggers, trigger],
    });
  }

  function handleNotesChange(value: string) {
    updateProfile({ ...profile, notes: value });
  }

  function handleRegister() {
    const validationError = validateProfileDraft(profile);
    if (validationError) {
      setError(validationError);
      return;
    }

    const completedProfile = buildCompletedProfile(profile);
    saveProfileDraft(completedProfile);
    router.push("/planner");
  }

  return {
    error,
    handleBack,
    handleEmailChange,
    handleKnowledgeChange,
    handleNameChange,
    handleNotesChange,
    handleRegister,
    handleSensitivityChange,
    handleTriggerToggle,
    profile,
    routeSummary,
  };
}
