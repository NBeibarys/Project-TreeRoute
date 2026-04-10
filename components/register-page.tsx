"use client";

import { ALLERGY_TRIGGER_OPTIONS } from "@/lib/constants";
import { useRegisterController } from "@/lib/register-controller";
import type { Sensitivity } from "@/lib/types";

export function RegisterPage() {
  const {
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
  } = useRegisterController();

  return (
    <main className="register-shell">
      <header className="marketing-topbar">
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
            <p>Create your allergy profile</p>
          </div>
        </div>
        <button className="ghost-link" onClick={handleBack} type="button">
          Back
        </button>
      </header>

      <section className="register-stage">
        <div className="register-layout">
          <article className="register-side-panel">
            <span className="eyebrow">Route saved</span>
            <h2>We kept your trip ready</h2>
            <p>
              Finish registration once and treeroute will continue with the route you entered on the landing page.
            </p>

            <div className="route-intent-card">
              <div>
                <span>Start</span>
                <strong>{routeSummary.origin.address}</strong>
              </div>
              <div className="route-intent-divider" />
              <div>
                <span>End</span>
                <strong>{routeSummary.destination.address}</strong>
              </div>
            </div>

            <div className="route-benefits">
              <span>Species-aware routing</span>
              <span>Wind-aware exposure</span>
              <span>Safer corridor ranking</span>
            </div>
          </article>

          <article className="register-card">
            <div className="register-copy">
              <span className="eyebrow">Required before routing</span>
              <h2>Create your treeroute profile</h2>
              <p>
                Tell us who you are and which tree species affect you. If you do not know your allergy triggers yet,
                treeroute will still build routes that minimize contact with trees in general.
              </p>
            </div>

            <div className="register-form-grid">
              <label className="field-label">
                Name
                <input
                  className="text-input"
                  onChange={(event) => handleNameChange(event.target.value)}
                  placeholder="Avery"
                  value={profile.name ?? ""}
                />
              </label>

              <label className="field-label">
                Email
                <input
                  className="text-input"
                  onChange={(event) => handleEmailChange(event.target.value)}
                  placeholder="avery@example.com"
                  type="email"
                  value={profile.email ?? ""}
                />
              </label>

              <label className="field-label">
                Sensitivity
                <div className="toggle-row">
                  {(["low", "medium", "high"] as Sensitivity[]).map((level) => (
                    <button
                      className={`toggle-chip ${profile.sensitivity === level ? "toggle-chip-active" : ""}`}
                      key={level}
                      onClick={() => handleSensitivityChange(level)}
                      type="button"
                    >
                      {level}
                    </button>
                  ))}
                </div>
              </label>

              <div className="field-label">
                Tree allergy knowledge
                <div className="toggle-row">
                  <button
                    className={`toggle-chip ${profile.knowsTreeTriggers ? "toggle-chip-active" : ""}`}
                    onClick={() => handleKnowledgeChange(true)}
                    type="button"
                  >
                    I know the tree species
                  </button>
                  <button
                    className={`toggle-chip ${!profile.knowsTreeTriggers ? "toggle-chip-active" : ""}`}
                    onClick={() => handleKnowledgeChange(false)}
                    type="button"
                  >
                    I don&apos;t know, avoid trees generally
                  </button>
                </div>
              </div>

              {profile.knowsTreeTriggers ? (
                <div className="field-label">
                  Tree triggers
                  <div className="trigger-grid">
                    {ALLERGY_TRIGGER_OPTIONS.map((trigger) => {
                      const active = profile.triggers.includes(trigger);
                      return (
                        <button
                          className={`trigger-chip ${active ? "trigger-chip-active" : ""}`}
                          key={trigger}
                          onClick={() => handleTriggerToggle(trigger)}
                          type="button"
                        >
                          {trigger}
                        </button>
                      );
                    })}
                  </div>
                </div>
              ) : (
                <div className="inline-notice">
                  We will minimize overall tree contact and use current pollen and weather conditions to rank routes.
                </div>
              )}

              <label className="field-label">
                Notes
                <textarea
                  className="text-area"
                  onChange={(event) => handleNotesChange(event.target.value)}
                  placeholder="Optional context for the routing engine"
                  rows={3}
                  value={profile.notes ?? ""}
                />
              </label>
            </div>

            <button className="primary-button register-submit" onClick={handleRegister} type="button">
              Create account and continue
            </button>

            {error ? <p className="error-line">{error}</p> : null}
          </article>
        </div>
      </section>
    </main>
  );
}
