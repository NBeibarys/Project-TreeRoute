# Project Map

This is the final local architecture of the app.

## Stack

- Frontend: Next.js 16 + React + TypeScript
- Backend: Python + FastAPI
- Model: Gemini 2.5 Flash
- Maps and live signals: Google Maps, Routes, Weather, and Pollen APIs
- Data layer: NYC tree-grid sample and generated tree-grid data

## Product Flow

The user flow is:

`/ -> /register -> /planner`

1. Landing collects the route intent.
2. Register collects the allergy profile.
3. Planner sends the request to FastAPI.
4. FastAPI ranks routes and returns explanations.
5. The planner renders route cards, map overlays, hotspots, and speech output.

## Frontend Map

### Routing and pages

- `app/page.tsx`
  Renders the landing screen.
- `app/register/page.tsx`
  Renders the register flow.
- `app/planner/page.tsx`
  Renders the planner flow.

### UI components

- `components/landing/landing-page.tsx`
  Landing screen UI.
- `components/register/register-page.tsx`
  Registration UI.
- `components/planner/pollen-safe-app.tsx`
  Planner UI.
- `components/landing/location-autocomplete.tsx`
  Google Places autocomplete input.
- `components/landing/voice-button.tsx`
  Browser speech recognition and voice-parse request flow.
- `components/planner/route-map.tsx`
  Google Maps rendering for routes and hotspots.
- `components/shared/site-brand.tsx`
  Shared persistent brand badge.

### Frontend logic

- `lib/landing/landing-controller.ts`
  Landing page behavior and navigation decisions.
- `lib/register/register-controller.ts`
  Registration form behavior.
- `lib/planner/planner-controller.ts`
  Planner orchestration on the client.
- `lib/storage/profile-store.ts`
  Profile validation and persistence.
- `lib/storage/route-draft-store.ts`
  Route draft persistence.
- `lib/register/registration-status.ts`
  Rules for deciding whether the user is already registered.
- `lib/planner/route-analysis-client.ts`
  Thin client wrapper for route analysis requests.
- `lib/api/fastapi-client.ts`
  Shared direct HTTP client for FastAPI.
- `lib/planner/route-summary-speech.ts`
  Speech synthesis for the planner summary.
- `lib/shared/constants.ts`
  Shared enums, labels, and storage keys.
- `lib/shared/types.ts`
  Shared TypeScript contracts between frontend modules.
- `lib/shared/polyline.ts`
  Polyline encode/decode helpers for map rendering.

## Backend Map

- `backend/app/main.py`
  FastAPI app, CORS, and HTTP endpoints.
- `backend/app/route_analysis.py`
  Main route-analysis use case orchestration.
- `backend/app/providers.py`
  External API calls and degraded fallback behavior.
- `backend/app/scoring.py`
  Route exposure scoring logic.
- `backend/app/tree_grid.py`
  Tree-grid loading and lookup.
- `backend/app/voice_parse.py`
  Voice transcript parsing with Gemini and local fallback.
- `backend/app/geometry.py`
  Shared math and route helper functions.
- `backend/app/models.py`
  Request and response models.

## Request Flows

### Voice flow

1. `components/landing/voice-button.tsx` captures browser speech.
2. The transcript is sent to `POST /voice-parse`.
3. `backend/app/voice_parse.py` returns `origin` and `destination`.
4. The landing screen fills the inputs with the parsed values.

### Planner flow

1. `lib/planner/planner-controller.ts` builds the request.
2. `lib/planner/route-analysis-client.ts` sends it to `POST /route-analysis`.
3. `backend/app/route_analysis.py` resolves routes, weather, and pollen.
4. `backend/app/scoring.py` ranks route exposure.
5. `backend/app/providers.py` generates readable explanations.
6. The planner renders the ranked routes and speaks the summary.

## Persistence

- The route draft is stored in `localStorage`.
- The registration profile is stored in `localStorage`.
- The backend tree-grid is loaded from `data/tree-grid.sample.json` or generated grid data.

## Local Commands

```bash
npm run dev
npm run dev:backend
npm run check:types
npm run test
npm run verify
npm run check:fastapi
```

## Mental Model

Use this shortcut when thinking about the app:

- `components/*` = what the user sees
- `lib/*controller.ts` = what the page does
- `lib/*store.ts` = what the browser remembers
- `lib/api/fastapi-client.ts` = how the browser talks to the backend
- `backend/app/*` = how the backend thinks
