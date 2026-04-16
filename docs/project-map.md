# Project Map

## Top Level

```text
frontend/   browser application
backend/    FastAPI backend
data/       sample and generated datasets
docs/       documentation and demo media
```

## Frontend Map

```text
frontend/
  app/
  features/
    landing/
    planner/
    register/
  shared/
    api/
    config/
    contracts/
    lib/
    storage/
    ui/
  public/
  tests/
```

- `frontend/app` owns route entrypoints and layout.
- `frontend/features/*` groups feature-specific UI and controller logic.
- `frontend/shared/*` holds shared frontend modules.

## Backend Map

```text
backend/
  app/
    api/
      main.py
      routes/
    services/
    domain/
    integrations/
    schemas/
  tests/
  scripts/
```

- `backend/app/api` owns HTTP concerns only.
- `backend/app/services` owns request orchestration.
- `backend/app/domain` owns business logic such as scoring and tree-grid lookups.
- `backend/app/integrations` owns external API calls.
- `backend/app/schemas` owns typed request/response models.

## Data Map

```text
data/
  sample/
  generated/
```

- `data/sample/tree-grid.sample.json` is the current checked-in demo dataset.
- `data/generated/` is where generated outputs should go.

## Main Runtime Flow

1. The frontend posts route requests to FastAPI.
2. FastAPI services fetch routes, weather, pollen, and civic data.
3. Backend domain code scores route exposure in Python.
4. Gemini generates grounded copy from backend results.
5. The frontend renders ranked routes, map overlays, and speech output.
