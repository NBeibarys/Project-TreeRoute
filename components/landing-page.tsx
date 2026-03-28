"use client";

import Script from "next/script";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { LocationAutocomplete } from "@/components/location-autocomplete";
import { VoiceButton } from "@/components/voice-button";
import { isRegistered } from "@/lib/profile";
import { loadRouteDraft, loadStoredProfile, saveRouteDraft } from "@/lib/storage";
import type { WaypointInput } from "@/lib/types";

const CLIENT_MAPS_KEY = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY;

export function LandingPage() {
  const router = useRouter();
  const [registered, setRegistered] = useState(false);
  const [origin, setOrigin] = useState<WaypointInput>({ address: "" });
  const [destination, setDestination] = useState<WaypointInput>({ address: "" });
  const [mapsReady, setMapsReady] = useState(false);

  useEffect(() => {
    setRegistered(isRegistered(loadStoredProfile()));
    const draft = loadRouteDraft();
    if (draft) {
      setOrigin(draft.origin);
      setDestination(draft.destination);
    }
  }, []);

  function handleRouteIntent() {
    saveRouteDraft({
      origin: { address: origin.address.trim() || "Washington Square Park, New York, NY" },
      destination: { address: destination.address.trim() || "Lincoln Center, New York, NY" },
    });
    router.push(registered ? "/planner" : "/register");
  }

  function handleVoiceResult(voiceOrigin: string, voiceDest: string) {
    if (voiceOrigin) setOrigin({ address: voiceOrigin });
    if (voiceDest) setDestination({ address: voiceDest });
  }

  return (
    <main className="marketing-shell">
      {CLIENT_MAPS_KEY ? (
        <Script
          src={`https://maps.googleapis.com/maps/api/js?key=${CLIENT_MAPS_KEY}&libraries=places`}
          strategy="afterInteractive"
          onReady={() => setMapsReady(true)}
        />
      ) : null}

      <header className="marketing-topbar">
        <div className="topbar-brand">
          <div className="topbar-logo">
            <svg fill="none" height="20" viewBox="0 0 24 24" width="20"><path d="M12 3C8 3 4 7.5 4 12c0 3.2 1.8 6 4.5 7.5V21l3.5-1.5 3.5 1.5v-1.5C18.2 18 20 15.2 20 12c0-4.5-4-9-8-9z" fill="#406b49"/><circle cx="12" cy="11" fill="#fbfb86" r="2.5"/></svg>
          </div>
          <div>
            <h1>treeroute</h1>
            <p>Pollen-safe walking routes for NYC</p>
          </div>
        </div>
        <button
          className="ghost-link"
          onClick={() => router.push(registered ? "/planner" : "/register")}
          type="button"
        >
          {registered ? "Open planner →" : "Get started"}
        </button>
      </header>

      <section className="marketing-stage">
        <article className="landing-card">
          <span className="eyebrow">AI-powered routing</span>
          <h2>Walk safer,<br />breathe easier.</h2>
          <p className="landing-support">
            treeroute ranks 2–3 walking routes by pollen exposure — combining NYC tree census data,
            live pollen levels, wind, and Gemini AI. The fastest path isn't always the safest one.
          </p>

          <label className="landing-field">
            <span>From</span>
            <LocationAutocomplete
              inputClassName="landing-input"
              mapsReady={mapsReady}
              onChange={setOrigin}
              placeholder="Starting location..."
              value={origin}
            />
          </label>

          <label className="landing-field">
            <span>To</span>
            <LocationAutocomplete
              inputClassName="landing-input"
              mapsReady={mapsReady}
              onChange={setDestination}
              placeholder="Destination..."
              value={destination}
            />
          </label>

          <div className="landing-mini-stats">
            <span>Street trees</span>
            <span>Live pollen</span>
            <span>Wind & humidity</span>
            <span>Gemini AI</span>
          </div>

          <VoiceButton onResult={handleVoiceResult} />

          <div className="voice-divider">
            <div className="voice-divider-line" />
            <span>or type above</span>
            <div className="voice-divider-line" />
          </div>

          <button className="landing-cta" onClick={handleRouteIntent} type="button">
            Find Safe Route →
          </button>

          <div className="landing-data-sources">
            {["NYC Open Data", "Google Pollen API", "Gemini 2.5 Flash"].map((label) => (
              <span key={label}>{label}</span>
            ))}
          </div>
        </article>

        <article className="landing-preview">
          <div className="preview-chrome">
            <div className="preview-google-bar">G</div>
            <div className="preview-heading">
              <strong>NYC Street Tree Census · 700k+ mapped trees</strong>
              <span>Pollen exposure scores updated in real-time</span>
            </div>
          </div>
          <div className="preview-grid">
            <div className="preview-story">
              <h3>The fastest path ≠ safest path</h3>
              <div className="preview-rule" />
              <p>
                treeroute maps 700,000+ NYC street trees to your allergy profile, then layers
                live pollen pressure, wind speed, and humidity to rank every route.
              </p>
              <p>
                Register once, pick your triggers — oak, birch, maple — and the planner steers
                you through lower-burden corridors instead of just the shortest path.
              </p>
              <div className="preview-route-list">
                {[
                  { label: "Route A — Broadway", score: 18, level: "low" },
                  { label: "Route B — 5th Ave", score: 54, level: "moderate" },
                  { label: "Route C — Park Ave", score: 81, level: "high" },
                ].map((r) => (
                  <div key={r.label} className="preview-route-item">
                    <div className="preview-route-header">
                      <span className="preview-route-label">{r.label}</span>
                      <span className={`risk-band risk-${r.level} preview-score-chip`}>Score {r.score}</span>
                    </div>
                    <div className="score-bar-track">
                      <div className={`score-bar-fill score-bar-fill-${r.level}`} style={{ width: `${r.score}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="preview-map">
              <div className="preview-search">Search New York City...</div>
              <div className="preview-tag">Tree density overlay</div>
              <div className="preview-map-label preview-label-manhattan">Manhattan</div>
              <div className="preview-map-label preview-label-queens">Queens</div>
              <div className="preview-map-label preview-label-brooklyn">Brooklyn</div>
              <div className="preview-stat preview-stat-queens">296,680<br />Mapped Trees</div>
              <div className="preview-stat preview-stat-brooklyn">255,055<br />Mapped Trees</div>
              <div className="preview-insight preview-insight-top">Low exposure corridor</div>
              <div className="preview-insight preview-insight-bottom">High pollen spread</div>
              <div className="preview-zoom preview-zoom-plus">+</div>
              <div className="preview-zoom preview-zoom-minus">−</div>
            </div>
          </div>
        </article>
      </section>
    </main>
  );
}
