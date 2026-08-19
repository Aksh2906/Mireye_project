"use client";

import { useEffect, useRef } from "react";
import maplibregl from "maplibre-gl";
import type { EvidenceRecord } from "@/lib/types";

export default function MapPanel({
  latitude,
  longitude,
  evidence = [],
}: {
  latitude: number;
  longitude: number;
  evidence?: EvidenceRecord[];
}) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    const map = new maplibregl.Map({
      container: ref.current,
      style: "https://demotiles.maplibre.org/style.json",
      center: [longitude, latitude],
      zoom: 11,
    });
    new maplibregl.Marker({ color: "#193f31" })
      .setLngLat([longitude, latitude])
      .addTo(map);
    map.on("load", () => {
      const features = evidence
        .filter(
          (x) =>
            x.geometry &&
            ["Point", "Polygon", "MultiPolygon"].includes(
              String(x.geometry.type),
            ),
        )
        .map((x) => ({
          type: "Feature" as const,
          properties: { field: x.field_name, scope: x.semantic_scope },
          geometry: x.geometry as unknown as GeoJSON.Geometry,
        }));
      if (!features.length) return;
      map.addSource("evidence", {
        type: "geojson",
        data: { type: "FeatureCollection", features },
      });
      map.addLayer({
        id: "evidence-fill",
        type: "fill",
        source: "evidence",
        filter: ["==", ["geometry-type"], "Polygon"],
        paint: { "fill-color": "#2f6b48", "fill-opacity": 0.22 },
      });
      map.addLayer({
        id: "evidence-points",
        type: "circle",
        source: "evidence",
        filter: ["==", ["geometry-type"], "Point"],
        paint: { "circle-radius": 5, "circle-color": "#bd792d" },
      });
    });
    return () => map.remove();
  }, [latitude, longitude, evidence]);
  return (
    <>
      <div ref={ref} className="map" />
      <p className="fine">
        Evidence geometry is contextual and does not imply a legal parcel
        boundary.
      </p>
    </>
  );
}
