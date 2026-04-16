from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.api.routes.route_analysis import router as route_analysis_router
from app.api.routes.voice_parse import router as voice_parse_router


load_dotenv(Path(__file__).resolve().parents[3] / ".env.local", override=False)


def get_allowed_origins():
    configured = os.getenv("CORS_ALLOW_ORIGINS", "").strip()
    if configured == "*":
        return ["*"]

    if configured:
        return [origin.strip() for origin in configured.split(",") if origin.strip()]

    return [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]


app = FastAPI(title="treeroute backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=False,
    allow_headers=["*"],
    allow_methods=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


app.include_router(route_analysis_router)
app.include_router(voice_parse_router)
