"use client";

import { useEffect, useRef } from "react";

import type { WaypointInput } from "@/shared/contracts/types";

interface LocationAutocompleteProps {
  label?: string;
  value: WaypointInput;
  onChange: (nextValue: WaypointInput) => void;
  mapsReady: boolean;
  placeholder: string;
  inputClassName?: string;
  labelClassName?: string;
}

export function LocationAutocomplete({
  label,
  value,
  onChange,
  mapsReady,
  placeholder,
  inputClassName = "text-input",
  labelClassName = "field-label",
}: LocationAutocompleteProps) {
  const inputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (!mapsReady || !inputRef.current || !window.google?.maps?.places) {
      return;
    }

    const autocomplete = new google.maps.places.Autocomplete(inputRef.current, {
      componentRestrictions: { country: ["us"] },
      fields: ["formatted_address", "geometry", "name"],
      types: ["geocode"],
    });

    const listener = autocomplete.addListener("place_changed", () => {
      const place = autocomplete.getPlace();
      const geometry = place.geometry?.location;

      onChange({
        address: place.formatted_address ?? place.name ?? inputRef.current?.value ?? value.address,
        location: geometry
          ? {
              lat: geometry.lat(),
              lng: geometry.lng(),
            }
          : undefined,
      });
    });

    return () => {
      listener.remove();
    };
  }, [mapsReady, onChange, value.address]);

  const input = (
    <input
      className={inputClassName}
      onChange={(event) =>
        onChange({
          address: event.target.value,
        })
      }
      placeholder={placeholder}
      ref={inputRef}
      value={value.address}
    />
  );

  if (!label) {
    return input;
  }

  return <label className={labelClassName}>{label}{input}</label>;
}
