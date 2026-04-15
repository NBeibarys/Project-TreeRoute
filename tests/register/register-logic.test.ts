import {
  buildCompletedProfile,
  DEFAULT_PROFILE_DRAFT,
  normalizeProfileDraft,
  validateProfileDraft,
} from "@/lib/storage/profile-store";
import type { UserProfile } from "@/lib/shared/types";

describe("register logic", () => {
  it("normalizes an empty profile to the default draft", () => {
    expect(normalizeProfileDraft(null)).toEqual(DEFAULT_PROFILE_DRAFT);
  });

  it("filters unknown triggers when normalizing a saved profile", () => {
    const profile = normalizeProfileDraft({
      name: "Avery",
      email: "avery@example.com",
      triggers: ["oak", "pine"],
      sensitivity: "high",
      notes: "",
      registrationComplete: false,
      knowsTreeTriggers: true,
    });

    expect(profile.triggers).toEqual(["oak"]);
  });

  it("requires a name before registration", () => {
    const profile: UserProfile = {
      ...DEFAULT_PROFILE_DRAFT,
      email: "avery@example.com",
    };

    expect(validateProfileDraft(profile)).toBe("Enter your name to continue.");
  });

  it("requires a selected trigger when the user knows tree species", () => {
    const profile: UserProfile = {
      ...DEFAULT_PROFILE_DRAFT,
      name: "Avery",
      email: "avery@example.com",
      knowsTreeTriggers: true,
      triggers: [],
    };

    expect(validateProfileDraft(profile)).toBe(
      "Choose at least one tree trigger, or switch to general tree avoidance.",
    );
  });

  it("builds a completed profile by trimming identity fields", () => {
    const completed = buildCompletedProfile({
      ...DEFAULT_PROFILE_DRAFT,
      name: "  Avery  ",
      email: "  avery@example.com ",
      notes: "  spring allergies  ",
      knowsTreeTriggers: false,
      triggers: ["oak"],
    });

    expect(completed.name).toBe("Avery");
    expect(completed.email).toBe("avery@example.com");
    expect(completed.notes).toBe("spring allergies");
    expect(completed.triggers).toEqual([]);
    expect(completed.registrationComplete).toBe(true);
  });
});
