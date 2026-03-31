# treeroute

treeroute is a hackathon-winning multimodal walking route planner for allergy-sensitive New Yorkers.

It helps people choose safer walking routes by combining:

- NYC street tree census data
- live pollen conditions
- live weather and wind
- Google Maps routing
- Gemini-generated grounded explanations

Instead of showing only the fastest path, treeroute ranks 2-3 walking routes by likely pollen exposure so users can walk safer, not just faster.

Built for the NYC Build With AI Hackathon.

Live demo:
https://treeroute-501252220143.us-central1.run.app/

Presentation deck:
https://docs.google.com/presentation/d/1Kf7AQ54lSMRo7GjB3PVdwe48MnMswPF4Mdgl18ub_s0/edit?usp=sharing

![treeroute demo](./docs/media/treeroute-demo.gif)

## Why It Stands Out

- Real public-interest use case: safer outdoor navigation for allergy-sensitive residents.
- Multimodal experience: voice in, visual map output, voice summary out.
- Strong AI usage: Gemini is used for voice parsing and grounded route explanation synthesis.
- Civic + live data blend: NYC Tree Census plus Google Routes, Pollen, and Weather APIs.
- End-to-end demo flow: landing page, registration, route planner, map, scoring, and explanation output.

## Core Experience

The product flow is:

`/ -> /register -> /planner`

1. A user enters a starting point and destination by typing or voice.
2. The route draft is saved locally.
3. The user registers once with allergy sensitivity and tree-trigger preferences.
4. The planner loads the saved route and analyzes alternative walking paths.
5. treeroute ranks the routes by expected pollen exposure and explains the recommendation.

## Multimodal UX

| Modality | Implementation |
|---|---|
| Speak | Web Speech API mic button for route input |
| Hear | `speechSynthesis` reads the best route recommendation aloud |
| See | Google Maps route overlay, markers, and hotspot visualization |

Voice input is parsed through `/api/voice-parse`, which uses Gemini with a local parser fallback.

## What The App Does

- Collects route intent on a branded landing page
- Requires a lightweight allergy profile before route analysis
- Supports specific tree-trigger selection or general tree avoidance
- Generates 2-3 walking route alternatives
- Scores routes using tree density, species overlap, pollen, wind, humidity, and sensitivity
- Displays route cards, exposure scores, and map hotspots
- Produces grounded natural-language explanations for why one route is safer

## Tech Stack

- Next.js 16 App Router
- React + TypeScript
- Google Maps JavaScript API
- Google Routes API
- Google Pollen API
- Google Weather API
- Google GenAI SDK with Gemini 2.5 Flash
- NYC 2015 Street Tree Census
- Vitest
- Docker + Cloud Run deployment path

## Architecture

```mermaid
flowchart LR
    A[Voice Input] --> B["voice-parse API"]
    C[Typed Input] --> D["route-analysis API"]
    B --> D

    D --> E[Google Routes API]
    D --> F[Google Pollen API]
    D --> G[Google Weather API]
    D --> H[NYC Tree Grid]

    E --> I[Exposure Scoring]
    F --> I
    G --> I
    H --> I

    I --> J[Gemini 2.5 Flash]

    J --> K[Map View]
    J --> L[Route Cards]
    J --> M[Voice Summary]
```

The route analysis backend supports two execution paths:

- A direct analysis pipeline in `lib/server/route-analysis.ts`
- An ADK-style single-turn orchestration agent in `lib/server/agent.ts`

The agent path declares tools for:

- fetching walking routes
- fetching pollen data
- fetching weather data
- scoring route exposure

Those signals are gathered in parallel, scored against the tree grid, and then passed to Gemini as grounded context for final explanations.

## Scoring Model

Route exposure is computed by:

1. Decoding each route polyline
2. Sampling points along the path
3. Looking up each sampled point in the tree-grid cells
4. Measuring canopy burden and species overlap with the user's profile
5. Adjusting the result with pollen, wind, humidity, route duration, and user sensitivity
6. Ranking routes from lowest to highest exposure

This means a slightly longer walk can rank higher if it avoids denser or more trigger-heavy canopy pockets.

## Demo Scenario

Try the app with:

- From: `Washington Square Park, New York, NY`
- To: `Lincoln Center, New York, NY`
- Triggers: `oak`, `birch`, `maple`
- Sensitivity: `medium` or `high`

Or say:

`from Washington Square Park to Lincoln Center`

This scenario is tuned to show a visible tradeoff between route speed and allergy exposure.

## Local Setup

1. Install dependencies:

```bash
npm install
```

2. Create a `.env.local` file in the project root:

```bash
NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=
GOOGLE_MAPS_API_KEY=
GOOGLE_POLLEN_API_KEY=
GOOGLE_WEATHER_API_KEY=
GOOGLE_AI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash
```

3. Start the app:

```bash
npm run dev
```

4. Open `http://localhost:3000`

The app includes graceful fallbacks, so some parts of the experience still work in degraded mode when certain live APIs are unavailable.

## Commands

```bash
npm run dev
npm run build
npm run test
npm run build-tree-grid -- ./StreetTreeCensus.csv ./data/tree-grid.generated.json
npm run capture:readme-demo
npm run build:readme-demo-gif
```

## Key Files

| File | Role |
|---|---|
| `components/landing-page.tsx` | Landing page and route-intent capture |
| `components/register-page.tsx` | Registration and allergy-profile onboarding |
| `components/pollen-safe-app.tsx` | Main planner UI, analysis flow, and speech output |
| `components/voice-button.tsx` | Speech recognition UI with Gemini + local parsing fallback |
| `components/route-map.tsx` | Route rendering and hotspot overlays on Google Maps |
| `app/api/voice-parse/route.ts` | Voice command parsing with Gemini |
| `app/api/route-analysis/route.ts` | Main API entry point for route analysis |
| `lib/server/agent.ts` | ADK-style agent orchestration path |
| `lib/server/route-analysis.ts` | Direct analysis pipeline with fallbacks |
| `lib/scoring.ts` | Core pollen-exposure scoring logic |
| `lib/tree-grid.ts` | Tree-grid lookup layer |
| `scripts/build-tree-grid.ts` | CSV-to-grid preprocessing script |

## Data

The repository includes a demo tree grid in `data/tree-grid.sample.json`.

That sample is based on the NYC 2015 Street Tree Census and is used to score route exposure by neighborhood canopy burden and top tree species.

## Deployment

The app is configured for standalone Next.js output and includes a `Dockerfile` suitable for Cloud Run.

Example:

```bash
gcloud run deploy treeroute \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_AI_API_KEY=...,GOOGLE_MAPS_API_KEY=...
```

## Team

| Name | Role | GitHub |
|---|---|---|
| Daniyar Abykhanov | Tech Lead | [@daniyar-udel](https://github.com/daniyar-udel) |
| Vera Vecherskaia | Expert | [@vvchrsk](https://github.com/vvchrsk) |
| Daniel Naumov | Expert | [@dnauminator](https://github.com/dnauminator) |
| Beibarys Nyussupov | Engineer | [@NBeibarys](https://github.com/NBeibarys) |
