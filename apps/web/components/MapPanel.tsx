"use client";

import { useEffect, useRef, useState } from "react";
import type { Feature, GeoJsonObject, Geometry } from "geojson";
import type * as Leaflet from "leaflet";
import type { AlternativeRecord, BoundaryRecord, EvidenceRecord } from "@/lib/types";

const escapeHtml = (value: unknown) =>
  String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");

type LayerName = "boundary" | "context" | "hazards" | "alternatives";

export default function MapPanel({ latitude, longitude, evidence = [], boundary = null, alternatives = [] }: {
  latitude: number;
  longitude: number;
  evidence?: EvidenceRecord[];
  boundary?: BoundaryRecord | null;
  alternatives?: AlternativeRecord[];
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [layers, setLayers] = useState<Record<LayerName, boolean>>({
    boundary: true,
    context: true,
    hazards: true,
    alternatives: true,
  });

  useEffect(() => {
    let disposed = false;
    let map: Leaflet.Map | undefined;

    const initialize = async () => {
      if (!ref.current) return;
      const L = await import("leaflet");
      if (disposed || !ref.current) return;
      map = L.map(ref.current, {
        center: [latitude, longitude], zoom: 11, zoomControl: true, preferCanvas: true,
      });

      const satellite = L.tileLayer(
        "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        {
          maxZoom: 19,
          attribution: "Tiles &copy; Esri &mdash; Source: Esri, Maxar, Earthstar Geographics, and the GIS User Community",
        },
      ).addTo(map);
      const streets = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      });
      L.control.layers({ Satellite: satellite, Streets: streets }, undefined, { position: "topright" }).addTo(map);
      L.control.scale({ imperial: true, metric: true }).addTo(map);

      const subject = L.circleMarker([latitude, longitude], {
        radius: 7, fillColor: "#193f31", fillOpacity: 1, color: "#ffffff", weight: 2,
      }).bindPopup("<strong>Subject property location</strong>");
      subject.addTo(map);
      const displayed = L.featureGroup().addTo(map);
      displayed.addLayer(subject);

      if (layers.context) {
        addFeatureCollection(
          L,
          map,
          evidence.filter((item) => item.source_type !== "HAZARD" && item.field_name !== "property_boundary" && item.geometry).map(evidenceFeature),
          "#2f6b48",
          displayed,
        );
      }
      if (layers.hazards) {
        addFeatureCollection(
          L,
          map,
          evidence.filter((item) => item.source_type === "HAZARD" && item.geometry).map(evidenceFeature),
          "#b64b35",
          displayed,
        );
      }
      if (layers.boundary && boundary) {
        const boundaryFeature: Feature = {
          type: "Feature",
          properties: {
            field: "Property boundary",
            scope: boundary.kind.replaceAll("_", " "),
            confidence: Math.round(boundary.confidence * 100),
            source: boundary.source_name,
            limitation: boundary.limitations[0] || "Not a legal survey.",
          },
          geometry: boundary.geometry as unknown as Geometry,
        };
        const boundaryLayer = L.geoJSON(boundaryFeature, {
          style: {
            color: boundary.kind === "analysis_geometry" ? "#f0a23a" : "#58e0a2",
            fillColor: "#1d5d43", fillOpacity: 0.2, weight: 4,
            dashArray: boundary.kind === "analysis_geometry" ? "8 7" : undefined,
          },
          onEachFeature: bindFeaturePopup,
        }).addTo(map);
        displayed.addLayer(boundaryLayer);
      }
      if (layers.alternatives) {
        addFeatureCollection(
          L,
          map,
          alternatives.filter((item) => item.location.coordinates.length >= 2).map((item) => ({
            type: "Feature" as const,
            properties: {
              field: item.title || "Nearby candidate",
              scope: `${item.distance_miles ?? "Unknown"} miles · ${item.investigation_depth}`,
              confidence: Math.round(item.evidence_quality * 100),
              source: item.source_url || "Configured listing provider",
              limitation: item.unknowns[0] || "Listing claims require independent verification.",
            },
            geometry: item.location as unknown as Geometry,
          })),
          "#f0a23a",
          displayed,
        );
      }

      const bounds = displayed.getBounds();
      if (boundary && bounds.isValid()) map.fitBounds(bounds, { padding: [36, 36], maxZoom: 16 });
      window.setTimeout(() => map?.invalidateSize(), 0);
    };

    void initialize();
    return () => {
      disposed = true;
      map?.remove();
    };
  }, [latitude, longitude, evidence, boundary, alternatives, layers]);

  return (
    <>
      <div className="map-toolbar" aria-label="Map evidence layers">
        {(Object.entries(layers) as Array<[LayerName, boolean]>).map(([name, enabled]) => (
          <button
            aria-pressed={enabled}
            className={enabled ? "layer-toggle active" : "layer-toggle"}
            key={name}
            onClick={() => setLayers((current) => ({ ...current, [name]: !current[name] }))}
            type="button"
          >
            {name}
          </button>
        ))}
      </div>
      <div ref={ref} className="map" aria-label="Satellite property evidence map" />
      <p className="fine">
        Satellite imagery is visual context, not a survey. {boundary
          ? `${boundary.kind.replaceAll("_", " ")} · ${boundary.area_acres.toLocaleString()} calculated acres · not a legal boundary`
          : "No parcel boundary is available; the marker and evidence are point context only."}
      </p>
    </>
  );
}

function evidenceFeature(item: EvidenceRecord): Feature {
  return {
    type: "Feature",
    properties: {
      field: item.field_name.replaceAll("_", " "),
      scope: item.semantic_scope || "Contextual evidence",
      confidence: Math.round(item.confidence * 100),
      source: `${item.source.publisher} · ${item.source.dataset}`,
      limitation: item.limitations[0] || "Review source details before relying on this evidence.",
    },
    geometry: item.geometry as unknown as Geometry,
  };
}

function addFeatureCollection(
  L: typeof Leaflet,
  map: Leaflet.Map,
  features: Feature[],
  color: string,
  displayed: Leaflet.FeatureGroup,
) {
  if (!features.length) return;
  const layer = L.geoJSON({ type: "FeatureCollection", features } as GeoJsonObject, {
    style: { color, fillColor: color, fillOpacity: 0.22, weight: 2 },
    pointToLayer: (_feature, latlng) => L.circleMarker(latlng, {
      radius: 6, fillColor: color, fillOpacity: 0.92, color: "#ffffff", weight: 2,
    }),
    onEachFeature: bindFeaturePopup,
  }).addTo(map);
  displayed.addLayer(layer);
}

function bindFeaturePopup(feature: Feature, layer: Leaflet.Layer) {
  const properties = feature.properties || {};
  const confidence = properties.confidence ?? "unknown";
  layer.bindPopup(
    `<strong>${escapeHtml(properties.field || "Evidence")}</strong>` +
      `<p>${escapeHtml(properties.scope)}</p>` +
      `<p>Confidence: ${escapeHtml(confidence)}${confidence === "unknown" ? "" : "%"}</p>` +
      `<small>${escapeHtml(properties.source)}<br>${escapeHtml(properties.limitation)}</small>`,
  );
}
