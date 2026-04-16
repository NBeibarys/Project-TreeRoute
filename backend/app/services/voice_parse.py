from __future__ import annotations

import json
import os
import re

from app.schemas.models import VoiceParseResponse


async def parse_voice_transcript(transcript: str) -> VoiceParseResponse:
    normalized_transcript = transcript.strip()
    if len(normalized_transcript) < 3:
        raise ValueError("Empty transcript")

    api_key = os.getenv("GOOGLE_AI_API_KEY") or ""
    if not api_key:
        return parse_transcript_locally(normalized_transcript)

    try:
        from google import genai  # type: ignore

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=os.getenv("GEMINI_MODEL") or "gemini-2.5-flash",
            contents=f'Extract origin and destination from this voice command: "{normalized_transcript}"',
            config={
                "system_instruction": (
                    "You extract walking origin and destination from voice commands. "
                    'Always respond with a single valid JSON object only - no markdown, no code fences, no extra text. '
                    'The JSON must have exactly two string fields: "origin" and "destination". '
                    "Both must be NYC location names. If only one location is mentioned, use empty string for origin. "
                    'If no locations found, return {"origin":"","destination":""}.'
                )
            },
        )

        text = getattr(response, "text", "") or ""
        parsed = json.loads(extract_json_object(text))

        return VoiceParseResponse(
            origin=str(parsed.get("origin") or "").strip(),
            destination=str(parsed.get("destination") or "").strip(),
        )
    except Exception:
        return parse_transcript_locally(normalized_transcript)


def parse_transcript_locally(text: str) -> VoiceParseResponse:
    normalized = text.strip()

    from_to = re.search(r"\bfrom\s+(.+?)\s+to\s+(.+)", normalized, re.IGNORECASE)
    if from_to:
        return VoiceParseResponse(
            origin=from_to.group(1).strip(),
            destination=from_to.group(2).strip(),
        )

    x_to_y = re.search(r"^(.+?)\s+to\s+(.+)$", normalized, re.IGNORECASE)
    if x_to_y:
        return VoiceParseResponse(
            origin=x_to_y.group(1).strip(),
            destination=x_to_y.group(2).strip(),
        )

    return VoiceParseResponse(origin="", destination=normalized)


def extract_json_object(text: str) -> str:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("Gemini response did not contain JSON.")
    return text[start : end + 1]
