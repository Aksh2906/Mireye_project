from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.connectors.http import async_client
from app.domain.models import Evidence, EvidenceSource, SourceType, ToolResult


class HazardAdapter:
    """Normalizes an approved hazard service without treating missing data as no exposure."""

    async def get_context(
        self,
        latitude: float,
        longitude: float,
        hazards: list[str],
        geometry: dict[str, Any] | None = None,
    ) -> ToolResult:
        settings = get_settings()
        if not settings.hazard_api_url:
            return ToolResult(
                tool_name="hazard.get_context",
                success=False,
                limitations=[],
            )
        headers = (
            {"Authorization": f"Bearer {settings.hazard_api_token}"}
            if settings.hazard_api_token
            else {}
        )
        try:
            async with async_client(timeout=60) as client:
                response = await client.post(
                    settings.hazard_api_url,
                    json={
                        "latitude": latitude,
                        "longitude": longitude,
                        "hazards": hazards,
                        "geometry": geometry,
                    },
                    headers=headers,
                )
                response.raise_for_status()
                payload = response.json()
        except Exception as exc:
            return ToolResult(
                tool_name="hazard.get_context",
                success=False,
                limitations=[f"Hazard provider unavailable: {type(exc).__name__}"],
            )
        source = payload.get("source", {}) if isinstance(payload, dict) else {}
        rows = payload.get("hazards", []) if isinstance(payload, dict) else []
        observations: list[Evidence] = []
        for row in rows:
            if not isinstance(row, dict) or not row.get("hazard"):
                continue
            hazard = str(row["hazard"]).casefold().replace(" ", "_")
            observations.append(
                Evidence(
                    source_type=SourceType.HAZARD,
                    source=EvidenceSource(
                        publisher=source.get("publisher", "Configured hazard provider"),
                        dataset=source.get("dataset", "Property hazard context"),
                        url=row.get("source_url") or source.get("url") or settings.hazard_api_url,
                        vintage=row.get("vintage") or source.get("vintage"),
                    ),
                    field_name=f"{hazard}_exposure",
                    value={
                        "level": row.get("exposure") or row.get("level") or "observed",
                        "severity": row.get("severity"),
                        "frequency": row.get("frequency"),
                        "affected_area_acres": row.get("affected_area_acres"),
                    },
                    geometry=row.get("geometry"),
                    spatial_resolution=row.get("spatial_resolution"),
                    temporal_resolution=row.get("temporal_resolution"),
                    semantic_scope=row.get("semantic_scope", "property hazard context"),
                    confidence=float(row.get("confidence", 0.6)),
                    limitations=row.get("limitations") or [],
                    raw_reference={"hazard": hazard, "provider_record_id": row.get("id")},
                )
            )
        return ToolResult(
            tool_name="hazard.get_context",
            success=bool(observations),
            observations=observations,
            limitations=[]
            if observations
            else ["Hazard provider returned no usable observations."],
        )
