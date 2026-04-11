import {
  buildRouteDraftSnapshot,
  DEFAULT_ROUTE_DRAFT,
} from "@/lib/storage/route-draft-store";
import { hasCompletedRegistration } from "@/lib/register/registration-status";
import type { UserProfile } from "@/lib/shared/types";

describe("landing logic", () => {
  it("fills empty route inputs with the default demo route", () => {
    const draft = buildRouteDraftSnapshot(
      { address: "   " },
      { address: "" },
    );

    expect(draft).toEqual(DEFAULT_ROUTE_DRAFT);
  });

  it("trims typed route values before saving", () => {
    const draft = buildRouteDraftSnapshot(
      { address: "  Times Square, New York, NY  " },
      { address: "  Bryant Park, New York, NY " },
    );

    expect(draft.origin.address).toBe("Times Square, New York, NY");
    expect(draft.destination.address).toBe("Bryant Park, New York, NY");
  });

  it("preserves selected map coordinates when a place was chosen from autocomplete", () => {
    const draft = buildRouteDraftSnapshot(
      { address: "Times Square, New York, NY", location: { lat: 40.758, lng: -73.9855 } },
      { address: "Bryant Park, New York, NY", location: { lat: 40.7536, lng: -73.9832 } },
    );

    expect(draft.origin.location).toEqual({ lat: 40.758, lng: -73.9855 });
    expect(draft.destination.location).toEqual({ lat: 40.7536, lng: -73.9832 });
  });

  it("recognizes a fully completed general-avoidance profile", () => {
    const profile: UserProfile = {
      name: "Avery",
      email: "avery@example.com",
      triggers: [],
      sensitivity: "medium",
      knowsTreeTriggers: false,
      registrationComplete: true,
    };

    expect(hasCompletedRegistration(profile)).toBe(true);
  });

  it("requires at least one trigger when the user says they know tree species", () => {
    const profile: UserProfile = {
      name: "Avery",
      email: "avery@example.com",
      triggers: [],
      sensitivity: "medium",
      knowsTreeTriggers: true,
      registrationComplete: true,
    };

    expect(hasCompletedRegistration(profile)).toBe(false);
  });

  it("treats legacy profiles with triggers but no knowsTreeTriggers flag as registered", () => {
    const legacyProfile = {
      name: "Avery",
      email: "avery@example.com",
      triggers: ["oak"],
      sensitivity: "medium",
      registrationComplete: true,
    } as UserProfile;

    expect(hasCompletedRegistration(legacyProfile)).toBe(true);
  });
});
