import type { LatLngLiteral } from "@/lib/shared/types";

export function decodePolyline(encoded: string): LatLngLiteral[] {
  let index = 0;
  let lat = 0;
  let lng = 0;
  const coordinates: LatLngLiteral[] = [];

  while (index < encoded.length) {
    let result = 0;
    let shift = 0;
    let byte: number;

    do {
      byte = encoded.charCodeAt(index++) - 63;
      result |= (byte & 0x1f) << shift;
      shift += 5;
    } while (byte >= 0x20);

    const deltaLat = result & 1 ? ~(result >> 1) : result >> 1;
    lat += deltaLat;

    result = 0;
    shift = 0;

    do {
      byte = encoded.charCodeAt(index++) - 63;
      result |= (byte & 0x1f) << shift;
      shift += 5;
    } while (byte >= 0x20);

    const deltaLng = result & 1 ? ~(result >> 1) : result >> 1;
    lng += deltaLng;

    coordinates.push({
      lat: lat / 1e5,
      lng: lng / 1e5,
    });
  }

  return coordinates;
}

export function encodePolyline(points: LatLngLiteral[]): string {
  let lastLat = 0;
  let lastLng = 0;

  return points
    .map((point) => {
      const lat = Math.round(point.lat * 1e5);
      const lng = Math.round(point.lng * 1e5);
      const encodedLat = encodeSignedNumber(lat - lastLat);
      const encodedLng = encodeSignedNumber(lng - lastLng);
      lastLat = lat;
      lastLng = lng;
      return `${encodedLat}${encodedLng}`;
    })
    .join("");
}

function encodeSignedNumber(value: number): string {
  let shifted = value < 0 ? ~(value << 1) : value << 1;
  let output = "";

  while (shifted >= 0x20) {
    output += String.fromCharCode((0x20 | (shifted & 0x1f)) + 63);
    shifted >>= 5;
  }

  output += String.fromCharCode(shifted + 63);
  return output;
}
