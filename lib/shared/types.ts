export type Sensitivity = "low" | "medium" | "high";
export type ExposureLevel = "low" | "moderate" | "high";
export type RoutingMode = "specific-tree-triggers" | "general-tree-avoidance";

export interface LatLngLiteral {
  lat: number;
  lng: number;
}

export interface UserProfile {
  name?: string;
  email?: string;
  triggers: string[];
  sensitivity: Sensitivity;
  notes?: string;
  registrationComplete?: boolean;
  knowsTreeTriggers: boolean;
}

export interface WaypointInput {
  address: string;
  location?: LatLngLiteral;
}

export interface RouteAnalysisRequest {
  origin: WaypointInput;
  destination: WaypointInput;
  profile: UserProfile;
}

export interface RouteHotspot {
  lat: number;
  lng: number;
  label: string;
  risk: number;
}

export interface RouteCandidate {
  id: string;
  label: string;
  polyline: string;
  durationMin: number;
  distanceMeters: number;
  exposureScore: number;
  exposureLevel: ExposureLevel;
  explanation: string;
  rationale: string[];
  hotspots: RouteHotspot[];
}

export interface WeatherSignal {
  description: string;
  windSpeedMph: number;
  humidity: number;
  temperatureF: number;
}

export interface PollenSignal {
  treeIndex: number;
  grassIndex: number;
  weedIndex: number;
  summary: string;
}

export interface CivicInsight {
  areaName: string;
  treeBurdenLevel: ExposureLevel;
  summary: string;
}

export interface RouteAnalysisResponse {
  originResolved: string;
  destinationResolved: string;
  originPoint: LatLngLiteral;
  destinationPoint: LatLngLiteral;
  summary: string;
  routingMode: RoutingMode;
  dataSources: string[];
  routes: RouteCandidate[];
  civicInsight: CivicInsight;
  weather: WeatherSignal;
  pollen: PollenSignal;
  fallbackMode: string[];
}

export interface TreeGridCell {
  key: string;
  center: LatLngLiteral;
  areaName: string;
  density: number;
  canopyScore: number;
  topSpecies: string[];
  speciesWeights: Record<string, number>;
}

export interface TreeGridData {
  version: string;
  origin: LatLngLiteral;
  latStep: number;
  lngStep: number;
  cellSizeMeters: number;
  cells: TreeGridCell[];
}

export interface GoogleRoute {
  id: string;
  polyline: string;
  durationMin: number;
  distanceMeters: number;
}

export interface ResolvedWaypoint {
  address: string;
  location: LatLngLiteral;
}

export interface RouteSignals {
  weather: WeatherSignal;
  pollen: PollenSignal;
}
