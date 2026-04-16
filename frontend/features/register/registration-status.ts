import { ALLERGY_TRIGGER_OPTIONS, PROFILE_STORAGE_KEY } from "@/shared/config/constants";
import type { UserProfile } from "@/shared/contracts/types";

export function loadStoredProfileSnapshot(): UserProfile | null {
  if (typeof window === "undefined") {
    return null;
  }

  try {
    const raw = window.localStorage.getItem(PROFILE_STORAGE_KEY);
    return raw ? (JSON.parse(raw) as UserProfile) : null;
  } catch {
    return null;
  }
}

export function hasCompletedRegistration(profile: UserProfile | null) {
  if (!profile) {
    return false;
  }

  const triggers = normalizeTriggers(profile.triggers);
  const knowsTreeTriggers = profile.knowsTreeTriggers ?? triggers.length > 0;
  const hasIdentity = Boolean(profile.name?.trim() && profile.email?.trim());
  const hasTreeMode = !knowsTreeTriggers || triggers.length > 0;

  return hasIdentity && hasTreeMode && Boolean(profile.registrationComplete);
}

function normalizeTriggers(triggers: UserProfile["triggers"] | undefined) {
  return ALLERGY_TRIGGER_OPTIONS.filter((trigger) => triggers?.includes(trigger));
}
