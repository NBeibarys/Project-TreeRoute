# FastAPI Backend

This folder is the runtime backend for the app.

## Step By Step Architecture

1. `app/main.py`
   Exposes the FastAPI app and HTTP endpoints for both `route-analysis` and `voice-parse`.

2. `app/route_analysis.py`
   Orchestrates the full request flow:
   validate input -> resolve waypoints -> fetch route/weather/pollen signals -> score routes -> generate grounded copy.

3. `app/voice_parse.py`
   Handles voice-command parsing with Gemini and a regex fallback.

4. `app/providers.py`
   Talks to external systems and fallbacks:
   Google Maps, Google Routes, Google Weather, Google Pollen, Gemini.

5. `app/scoring.py`
   Pure domain logic for ranking route exposure.

6. `app/tree_grid.py`
   Loads the NYC tree-grid data and resolves nearby canopy cells.

7. `app/geometry.py`
   Small reusable math helpers such as distance, midpoint, polyline encoding, and route sampling.

## Frontend Connection

The browser calls FastAPI directly.

The frontend should be configured with:

```bash
NEXT_PUBLIC_FASTAPI_BASE_URL=http://localhost:8000
```

If frontend and backend run on different origins, FastAPI must also allow the frontend origin through CORS.

## Local Run

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
```

3. Start FastAPI from the repo root:

```bash
npm run dev:backend
```

4. Point the Next.js frontend to the Python backend:

```bash
NEXT_PUBLIC_FASTAPI_BASE_URL=http://localhost:8000
```

5. Allow the frontend origin:

```bash
CORS_ALLOW_ORIGINS=http://localhost:3000
```

6. Then run this from the frontend app:

```bash
npm run verify
npm run check:fastapi
```

## Docker

You can also build the backend as a standalone container:

```bash
docker build -f backend/Dockerfile -t treeroute-fastapi .
docker run -p 8000:8000 --env-file .env.local treeroute-fastapi
```

## Required Environment Variables

```bash
GOOGLE_MAPS_API_KEY=
GOOGLE_POLLEN_API_KEY=
GOOGLE_WEATHER_API_KEY=
GOOGLE_AI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash
CORS_ALLOW_ORIGINS=http://localhost:3000
```

FastAPI also supports degraded fallback behavior when some live APIs are unavailable.
