import { ALLERGY_TRIGGER_OPTIONS, PROFILE_STORAGE_KEY } from "@/lib/shared/constants";
import type { UserProfile } from "@/lib/shared/types";

export const DEFAULT_PROFILE_DRAFT: UserProfile = {
  name: "",
  email: "",
  triggers: [],
  sensitivity: "medium",
  notes: "",
  registrationComplete: false,
  knowsTreeTriggers: true,
};

export function loadProfileDraft(): UserProfile | null {
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

export function saveProfileDraft(profile: UserProfile) {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(PROFILE_STORAGE_KEY, JSON.stringify(profile));
}

export function clearProfileDraft() {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.removeItem(PROFILE_STORAGE_KEY);
}

export function normalizeProfileDraft(profile: UserProfile | null): UserProfile {
  if (!profile) {
    return DEFAULT_PROFILE_DRAFT;
  }

  const knownTriggers = ALLERGY_TRIGGER_OPTIONS.filter((trigger) => profile.triggers?.includes(trigger));

  return {
    ...DEFAULT_PROFILE_DRAFT,
    ...profile,
    triggers: knownTriggers,
    knowsTreeTriggers: profile.knowsTreeTriggers ?? knownTriggers.length > 0,
    registrationComplete: profile.registrationComplete ?? false,
  };
}

export function validateProfileDraft(profile: UserProfile) {
  if (!profile.name?.trim()) {
    return "Enter your name to continue.";
  }

  if (!profile.email?.trim()) {
    return "Enter your email to continue.";
  }

  if (profile.knowsTreeTriggers && !profile.triggers.length) {
    return "Choose at least one tree trigger, or switch to general tree avoidance.";
  }

  return "";
}

export function buildCompletedProfile(profile: UserProfile): UserProfile {
  return {
    ...profile,
    name: profile.name?.trim() ?? "",
    email: profile.email?.trim() ?? "",
    notes: profile.notes?.trim() ?? "",
    registrationComplete: true,
    triggers: profile.knowsTreeTriggers ? profile.triggers : [],
  };
}
