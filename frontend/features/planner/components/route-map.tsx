"use client";

import { useEffect, useRef } from "react";

import { decodePolyline } from "@/shared/lib/polyline";
import type { LatLngLiteral, RouteCandidate, RouteHotspot } from "@/shared/contracts/types";

interface RouteMapProps {
  apiKey?: string;
  mapsReady: boolean;
  origin: LatLngLiteral;
  destination: LatLngLiteral;
  routes: RouteCandidate[];
  selectedRouteId: string;
  onSelectRoute: (routeId: string) => void;
}

const ROUTE_COLORS = ["#406b49", "#d97706", "#dc2626"];

export function RouteMap({
  apiKey,
  mapsReady,
  origin,
  destination,
  routes,
  selectedRouteId,
  onSelectRoute,
}: RouteMapProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<google.maps.Map | null>(null);
  const overlaysRef = useRef<Array<google.maps.Polyline | google.maps.Marker>>([]);

  useEffect(() => {
    if (!mapsReady || !containerRef.current || !window.google?.maps) {
      return;
    }

    if (!mapRef.current) {
      mapRef.current = new google.maps.Map(containerRef.current, {
        center: origin,
        zoom: 13,
        disableDefaultUI: true,
        zoomControl: true,
        gestureHandling: "greedy",
      });
    }

    overlaysRef.current.forEach((overlay) => overlay.setMap(null));
    overlaysRef.current = [];

    const bounds = new google.maps.LatLngBounds();
    bounds.extend(origin);
    bounds.extend(destination);

    routes.forEach((route, index) => {
      const path = decodePolyline(route.polyline);
      path.forEach((point) => bounds.extend(point));

      const polyline = new google.maps.Polyline({
        map: mapRef.current,
        path,
        strokeColor: ROUTE_COLORS[index % ROUTE_COLORS.length],
        strokeOpacity: route.id === selectedRouteId ? 0.95 : 0.45,
        strokeWeight: route.id === selectedRouteId ? 6 : 4,
      });

      polyline.addListener("click", () => onSelectRoute(route.id));
      overlaysRef.current.push(polyline);
    });

    [origin, destination].forEach((point, index) => {
      const marker = new google.maps.Marker({
        map: mapRef.current,
        position: point,
        label: index === 0 ? "A" : "B",
      });

      overlaysRef.current.push(marker);
    });

    const selectedRoute = routes.find((route) => route.id === selectedRouteId);
    (selectedRoute?.hotspots ?? []).forEach((hotspot) => {
      const marker = new google.maps.Marker({
        map: mapRef.current,
        position: hotspot,
        icon: buildHotspotIcon(hotspot),
        title: `${hotspot.label}: risk ${hotspot.risk}`,
      });

      overlaysRef.current.push(marker);
    });

    mapRef.current.fitBounds(bounds, 56);
  }, [destination, mapsReady, onSelectRoute, origin, routes, selectedRouteId]);

  if (!apiKey) {
    return (
      <div className="planner-map-placeholder">
        Map preview activates once NEXT_PUBLIC_GOOGLE_MAPS_API_KEY is configured.
      </div>
    );
  }

  return <div className="route-map" ref={containerRef} />;
}

function buildHotspotIcon(hotspot: RouteHotspot): google.maps.Symbol {
  return {
    path: google.maps.SymbolPath.CIRCLE,
    fillColor: hotspot.risk > 60 ? "#dc2626" : "#d97706",
    fillOpacity: 1,
    strokeColor: "#f6f6f6",
    strokeWeight: 2,
    scale: hotspot.risk > 60 ? 7 : 5,
  };
}
