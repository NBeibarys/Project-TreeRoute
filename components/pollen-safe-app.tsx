"use client";

import Link from "next/link";
import Script from "next/script";

import { LocationAutocomplete } from "@/components/location-autocomplete";
import { RouteMap } from "@/components/route-map";
import { VoiceButton } from "@/components/voice-button";
import { EXPOSURE_LABELS } from "@/lib/constants";
import { usePlannerController } from "@/lib/planner-controller";

const CLIENT_MAPS_KEY = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY;

export function PollenSafeApp() {
  const {
    analysis,
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
  } = usePlannerController();

  if (!ready) {
    return <main className="planner-loading">Loading your treeroute profile...</main>;
  }

  return (
    <main className="planner-shell">
      {CLIENT_MAPS_KEY ? (
        <Script
          src={`https://maps.googleapis.com/maps/api/js?key=${CLIENT_MAPS_KEY}&libraries=places`}
          strategy="afterInteractive"
          onReady={() => setMapsReady(true)}
        />
      ) : null}

      <header className="marketing-topbar planner-topbar">
        <div className="topbar-brand">
          <div className="topbar-logo">
            <svg fill="none" height="20" viewBox="0 0 24 24" width="20">
              <path
                d="M12 3C8 3 4 7.5 4 12c0 3.2 1.8 6 4.5 7.5V21l3.5-1.5 3.5 1.5v-1.5C18.2 18 20 15.2 20 12c0-4.5-4-9-8-9z"
                fill="#406b49"
              />
              <circle cx="12" cy="11" fill="#fbfb86" r="2.5" />
            </svg>
          </div>
          <div>
            <h1>treeroute</h1>
            <p>Pollen exposure routing | NYC</p>
          </div>
        </div>
        <div className="planner-actions">
          <Link className="ghost-link" href="/register">
            Edit profile
          </Link>
          <button className="ghost-link" onClick={handleResetRegistration} type="button">
            Sign out
          </button>
        </div>
      </header>

      <section className="planner-grid">
        <div className="planner-sidebar">
          <article className="profile-summary-card">
            <span className="eyebrow">Registered profile</span>
            <h2>{profile.name}</h2>
            <p>{profile.email}</p>
            <div className="signal-row">
              <SignalPill label="Sensitivity" value={profile.sensitivity} />
              <SignalPill
                label="Mode"
                value={profile.knowsTreeTriggers && profile.triggers.length ? "Specific trees" : "General avoidance"}
              />
            </div>
            <div className="signal-row">
              <SignalPill
                label="Trees"
                value={profile.knowsTreeTriggers && profile.triggers.length ? profile.triggers.join(", ") : "All trees"}
              />
            </div>
            <p className="profile-summary-note">
              treeroute is using your saved allergy setup to evaluate expected pollen exposure across route alternatives.
            </p>
          </article>

          <form className="planner-panel-card" onSubmit={handleAnalyze}>
            <div className="planner-panel-header">
              <div>
                <span className="eyebrow">Route planner</span>
                <h2>Plan your route</h2>
              </div>
              <span className="status-chip">{loading ? "Analyzing..." : "Walking mode"}</span>
            </div>

            <div className="planner-panel-copy">
              Enter start and end points. We will rank 2-3 walking routes based on tree species, pollen conditions,
              wind, and humidity.
            </div>

            <LocationAutocomplete
              label="Starting location"
              labelClassName="field-label"
              mapsReady={mapsReady}
              onChange={handleOriginChange}
              placeholder="Starting location..."
              value={origin}
            />
            <LocationAutocomplete
              label="Destination"
              labelClassName="field-label"
              mapsReady={mapsReady}
              onChange={handleDestinationChange}
              placeholder="Destination..."
              value={destination}
            />

            <VoiceButton disabled={loading} onResult={handleVoiceResult} />

            <button className="planner-submit" disabled={loading} type="submit">
              {loading ? "Building Route..." : "Find Safe Route"}
            </button>

            <p className="status-line">{statusLine}</p>
            {error ? <p className="error-line">{error}</p> : null}
          </form>
        </div>

        <div className="planner-content">
          <section className="planner-map-card">
            <div className="planner-map-header">
              <div>
                <span className="eyebrow">Live route view</span>
                <h2>{selectedRoute?.label ?? "Route preview"}</h2>
              </div>
              <span className="recommendation-pill">
                {selectedRoute ? EXPOSURE_LABELS[selectedRoute.exposureLevel] : "Awaiting route"}
              </span>
            </div>

            {analysis ? (
              <RouteMap
                apiKey={CLIENT_MAPS_KEY}
                mapsReady={mapsReady}
                origin={analysis.originPoint}
                destination={analysis.destinationPoint}
                routes={analysis.routes}
                selectedRouteId={selectedRouteId}
                onSelectRoute={setSelectedRouteId}
              />
            ) : (
              <div className="planner-map-placeholder">
                Build your first route to see the safest corridor based on mapped trees, pollen, and weather.
              </div>
            )}
          </section>

          {analysis ? (
            <>
              <section className="results-grid">
                <article className="insight-card">
                  <p className="section-kicker">AI Recommendation</p>
                  <h3>{analysis.summary}</h3>
                  <p className="insight-support">
                    Balances mapped tree exposure with live environmental conditions, not just speed.
                  </p>
                  <div className="signal-row signal-row-spaced">
                    <SignalPill label="Tree pollen" value={String(analysis.pollen.treeIndex)} />
                    <SignalPill label="Wind" value={`${Math.round(analysis.weather.windSpeedMph)} mph`} />
                    <SignalPill label="Humidity" value={`${Math.round(analysis.weather.humidity)}%`} />
                  </div>
                </article>

                <article className="insight-card civic-card">
                  <p className="section-kicker">Area risk | NYC Open Data</p>
                  <h3>{analysis.civicInsight.areaName}</h3>
                  <p>{analysis.civicInsight.summary}</p>
                  <span className={`risk-band risk-${analysis.civicInsight.treeBurdenLevel} risk-band-spaced`}>
                    Tree burden: {EXPOSURE_LABELS[analysis.civicInsight.treeBurdenLevel]}
                  </span>
                </article>
              </section>

              <section className="route-list">
                {analysis.routes.map((route, index) => (
                  <button
                    className={`route-card ${route.id === selectedRouteId ? "route-card-active" : ""}`}
                    key={route.id}
                    onClick={() => setSelectedRouteId(route.id)}
                    type="button"
                  >
                    <div className="route-card-header">
                      <div>
                        <p className="route-rank">{index === 0 ? "Recommended" : `Alternative ${index}`}</p>
                        <h3>{route.label}</h3>
                      </div>
                      <span className={`risk-band risk-${route.exposureLevel}`}>
                        {EXPOSURE_LABELS[route.exposureLevel]}
                      </span>
                    </div>

                    <div className="score-bar-wrap">
                      <div className="score-bar-label">
                        <span>Exposure score</span>
                        <span>{route.exposureScore} / 100</span>
                      </div>
                      <div className="score-bar-track">
                        <div
                          className={`score-bar-fill score-bar-fill-${route.exposureLevel}`}
                          style={{ width: `${route.exposureScore}%` }}
                        />
                      </div>
                    </div>

                    <div className="route-meta">
                      <span>{route.durationMin} min walk</span>
                      <span>{Math.round((route.distanceMeters / 1609.34) * 10) / 10} mi</span>
                    </div>

                    <p className="route-explanation">{route.explanation}</p>
                    <div className="rationale-list">
                      {route.rationale.map((item) => (
                        <span className="rationale-pill" key={item}>
                          {item}
                        </span>
                      ))}
                    </div>
                  </button>
                ))}
              </section>
            </>
          ) : (
            <section className="empty-state planner-empty-state">
              <p className="section-kicker">Ready to route</p>
              <h2>Use the card on the left to build your first route.</h2>
              <p>
                Treeroute only becomes available after registration. Your saved allergy profile is already attached to
                the analysis, so the planner is now ready for route generation.
              </p>
            </section>
          )}
        </div>
      </section>
    </main>
  );
}

function SignalPill({ label, value }: { label: string; value: string }) {
  return (
    <span className="source-pill">
      {label}: <strong style={{ color: "var(--ink)" }}>{value}</strong>
    </span>
  );
}
