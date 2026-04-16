from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Sensitivity = Literal["low", "medium", "high"]
ExposureLevel = Literal["low", "moderate", "high"]
RoutingMode = Literal["specific-tree-triggers", "general-tree-avoidance"]


class LatLngLiteral(BaseModel):
    lat: float
    lng: float


class UserProfile(BaseModel):
    name: str | None = None
    email: str | None = None
    triggers: list[str] = Field(default_factory=list)
    sensitivity: Sensitivity
    notes: str | None = None
    registrationComplete: bool | None = None
    knowsTreeTriggers: bool


class WaypointInput(BaseModel):
    address: str = ""
    location: LatLngLiteral | None = None


class RouteAnalysisRequest(BaseModel):
    origin: WaypointInput
    destination: WaypointInput
    profile: UserProfile


class VoiceParseRequest(BaseModel):
    transcript: str


class VoiceParseResponse(BaseModel):
    origin: str
    destination: str


class RouteHotspot(BaseModel):
    lat: float
    lng: float
    label: str
    risk: float


class RouteCandidate(BaseModel):
    id: str
    label: str
    polyline: str
    durationMin: float
    distanceMeters: float
    exposureScore: float
    exposureLevel: ExposureLevel
    explanation: str
    rationale: list[str]
    hotspots: list[RouteHotspot]


class WeatherSignal(BaseModel):
    description: str
    windSpeedMph: float
    humidity: float
    temperatureF: float


class PollenSignal(BaseModel):
    treeIndex: float
    grassIndex: float
    weedIndex: float
    summary: str


class CivicInsight(BaseModel):
    areaName: str
    treeBurdenLevel: ExposureLevel
    summary: str


class RouteAnalysisResponse(BaseModel):
    originResolved: str
    destinationResolved: str
    originPoint: LatLngLiteral
    destinationPoint: LatLngLiteral
    summary: str
    routingMode: RoutingMode
    dataSources: list[str]
    routes: list[RouteCandidate]
    civicInsight: CivicInsight
    weather: WeatherSignal
    pollen: PollenSignal
    fallbackMode: list[str]


class TreeGridCell(BaseModel):
    key: str
    center: LatLngLiteral
    areaName: str
    density: float
    canopyScore: float
    topSpecies: list[str]
    speciesWeights: dict[str, float]


class TreeGridData(BaseModel):
    version: str
    origin: LatLngLiteral
    latStep: float
    lngStep: float
    cellSizeMeters: float
    cells: list[TreeGridCell]


class GoogleRoute(BaseModel):
    id: str
    polyline: str
    durationMin: float
    distanceMeters: float


class ResolvedWaypoint(BaseModel):
    address: str
    location: LatLngLiteral
