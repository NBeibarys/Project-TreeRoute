from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from .models import RouteAnalysisRequest, VoiceParseRequest
from .route_analysis import analyze_route_request
from .voice_parse import parse_voice_transcript


load_dotenv(Path(__file__).resolve().parents[2] / ".env.local", override=False)


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


@app.post("/route-analysis")
async def route_analysis(request: RouteAnalysisRequest):
    try:
        return await analyze_route_request(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/voice-parse")
async def voice_parse(request: VoiceParseRequest):
    try:
        return await parse_voice_transcript(request.transcript)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
