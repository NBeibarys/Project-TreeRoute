from __future__ import annotations

import json
import os
import sys
from urllib import error, request

BASE_URL = (
    os.getenv("FASTAPI_BASE_URL", "").strip()
    or os.getenv("NEXT_PUBLIC_FASTAPI_BASE_URL", "").strip()
    or "http://localhost:8000"
)


def main():
    health_response = fetch_json(f"{BASE_URL}/health")
    assert_condition(
        health_response["status"] == 200,
        f'health returned {health_response["status"]}: {json.dumps(health_response["body"])}',
    )
    assert_condition(
        health_response["body"].get("status") == "ok",
        f'Expected health status to be "ok", got {json.dumps(health_response["body"])}',
    )

    voice_response = fetch_json(
        f"{BASE_URL}/voice-parse",
        payload={"transcript": "Union Square to Lincoln Center"},
    )
    assert_condition(
        voice_response["status"] == 200,
        f'voice-parse returned {voice_response["status"]}: {json.dumps(voice_response["body"])}',
    )

    route_response = fetch_json(
        f"{BASE_URL}/route-analysis",
        payload={
            "origin": {
                "address": "Start",
                "location": {"lat": 40.74, "lng": -73.984},
            },
            "destination": {
                "address": "End",
                "location": {"lat": 40.788, "lng": -73.984},
            },
            "profile": {
                "triggers": [],
                "sensitivity": "medium",
                "knowsTreeTriggers": False,
            },
        },
    )
    assert_condition(
        route_response["status"] == 200,
        f'route-analysis returned {route_response["status"]}: {json.dumps(route_response["body"])}',
    )

    print("FastAPI is healthy and serving voice-parse and route-analysis directly.")


def fetch_json(url: str, payload: dict | None = None):
    data = None
    headers = {}

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = request.Request(
        url,
        data=data,
        headers=headers,
        method="POST" if payload is not None else "GET",
    )

    try:
        with request.urlopen(req) as response:
            body = response.read().decode("utf-8")
            return {
                "status": response.status,
                "body": json.loads(body) if body else None,
            }
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        return {
            "status": exc.code,
            "body": json.loads(body) if body else None,
        }


def assert_condition(condition: bool, message: str):
    if not condition:
        raise RuntimeError(message)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
