from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas.models import VoiceParseRequest
from app.services.voice_parse import parse_voice_transcript

router = APIRouter()


@router.post("/voice-parse")
async def voice_parse(request: VoiceParseRequest):
    try:
        return await parse_voice_transcript(request.transcript)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
