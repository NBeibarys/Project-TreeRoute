from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas.models import RouteAnalysisRequest
from app.services.route_analysis import analyze_route_request

router = APIRouter()


@router.post("/route-analysis")
async def route_analysis(request: RouteAnalysisRequest):
    try:
        return await analyze_route_request(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
