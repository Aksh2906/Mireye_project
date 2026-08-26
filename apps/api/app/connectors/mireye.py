from __future__ import annotations

import asyncio
from typing import Any

from app.config import get_settings
from app.connectors.cache import provider_cache
from app.connectors.http import async_client
from app.domain.models import Evidence, EvidenceSource, SourceType, ToolResult

# Default fields relevant to agricultural property investigations.
_DEFAULT_FIELDS = [
    "elevation",
    "slope_degrees",
    "soil_drainage_class",
    "within_floodplain_polygon",
    "intersects_wetland",
    "wetland_type",
    "nearest_wetland_distance_m",
    "coast_distance_m",
    "lcms_class",
    "land_use_class",
    "tree_canopy_pct",
    "cdl_class",
    "dominant_crop_5y",
]


class MireyeRESTAdapter:
    """Mireye REST API adapter using /v1/fetch and /v1/meta/fields."""

    def __init__(self) -> None:
        self.settings = get_settings()

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if self.settings.mireye_api_token:
            headers["Authorization"] = f"Bearer {self.settings.mireye_api_token}"
        return headers

    def _url(self, path: str) -> str:
        base = self.settings.mireye_api_url.rstrip("/")
        return f"{base}{path}"

    async def get_field_catalog(self) -> list[dict[str, Any]]:
        """GET /v1/meta/fields — public, no token needed."""
        try:
            async with async_client(timeout=30) as client:
                response = await client.get(self._url("/v1/meta/fields"))
                response.raise_for_status()
                return response.json()
        except Exception:
            return []

    @staticmethod
    def _normalize_fetch_response(
        data: dict[str, Any],
        latitude: float,
        longitude: float,
        requested_fields: list[str] | None,
    ) -> list[Evidence]:
        """Convert a /v1/fetch response into Evidence items."""
        api_url = data.get("resolved_location", {}).get("source", "coordinate")
        fields = data.get("fields", {})
        observations: list[Evidence] = []

        # Overall physical_context evidence with the full payload
        base_source = EvidenceSource(
            publisher="Mireye",
            dataset="/v1/fetch",
            url="https://api.mireye.com/v1/fetch",
        )
        observations.append(
            Evidence(
                source_type=SourceType.MIREYE,
                source=base_source,
                field_name="physical_context",
                value=fields,
                geometry={"type": "Point", "coordinates": [longitude, latitude]},
                semantic_scope="physical context at requested coordinate",
                confidence=0.75,
                limitations=[
                    "Point context does not establish a legal parcel boundary or property right."
                ],
                raw_reference={
                    "tool": "/v1/fetch",
                    "arguments": {
                        "lat": latitude,
                        "lng": longitude,
                        "fields": requested_fields,
                    },
                    "location_source": api_url,
                },
            )
        )

        # Individual field-level evidence
        for field_name, field_data in fields.items():
            if not isinstance(field_data, dict):
                continue
            # Skip failed fields
            status = field_data.get("status", "ok")
            if status == "failed":
                continue

            value = field_data.get("value")
            source_name = field_data.get("source", "Mireye")
            source_url = field_data.get("source_url", "https://api.mireye.com")
            confidence_str = field_data.get("confidence", "medium")
            confidence_map = {"high": 0.85, "medium": 0.7, "low": 0.5, "unknown": 0.5}
            confidence = confidence_map.get(confidence_str, 0.7)

            field_source = EvidenceSource(
                publisher="Mireye",
                dataset=source_name,
                url=source_url,
                vintage=field_data.get("dataset_vintage"),
            )

            is_property_scope = False
            geometry: dict[str, Any] = {
                "type": "Point",
                "coordinates": [longitude, latitude],
            }

            observations.append(
                Evidence(
                    source_type=SourceType.MIREYE,
                    source=field_source,
                    field_name=str(field_name),
                    value=value,
                    unit=field_data.get("unit"),
                    geometry=geometry,
                    semantic_scope=(
                        "property cultivated footprint"
                        if field_name == "cultivated_acres" and is_property_scope
                        else "provider physical field"
                    ),
                    confidence=confidence,
                    limitations=[
                        "Provider field context is physical evidence and does not establish legal rights."
                    ]
                    + ([field_data["notes"]] if field_data.get("notes") else []),
                    raw_reference={
                        "tool": "/v1/fetch",
                        "arguments": {"lat": latitude, "lng": longitude},
                        "provider_field": field_name,
                        "fetched_at": field_data.get("fetched_at"),
                    },
                )
            )

        return observations

    # Keep _normalize_context for backward compatibility with tests
    def _normalize_context(
        self,
        provider_tool: str,
        args: dict[str, Any],
        result: dict[str, Any],
        latitude: float,
        longitude: float,
    ) -> list[Evidence]:
        """Backward-compatible normalization. Handles both MCP-style
        structuredContent payloads (for tests) and REST API responses."""
        # Handle MCP-style structuredContent (used by existing tests)
        if "structuredContent" in result:
            payload = result["structuredContent"]
        else:
            content = result.get("content", [])
            payload = content
            import json

            for item in content if isinstance(content, list) else []:
                if isinstance(item, dict) and item.get("type") == "text":
                    try:
                        payload = json.loads(item.get("text", ""))
                        break
                    except (TypeError, json.JSONDecodeError):
                        continue

        base_source = EvidenceSource(
            publisher="Mireye",
            dataset=provider_tool,
            url=self.settings.mireye_api_url,
        )
        observations = [
            Evidence(
                source_type=SourceType.MIREYE,
                source=base_source,
                field_name="physical_context",
                value=payload,
                geometry={"type": "Point", "coordinates": [longitude, latitude]},
                semantic_scope="physical context at requested coordinate",
                confidence=0.75,
                limitations=[
                    "Point context does not establish a legal parcel boundary or property right."
                ],
                raw_reference={"tool": provider_tool, "arguments": args},
            )
        ]
        if isinstance(payload, dict):
            provider_geometry = payload.get("geometry")
            for field_name, value in payload.items():
                if field_name in {"geometry", "metadata", "source", "citations"}:
                    continue
                geometry = (
                    provider_geometry
                    if isinstance(provider_geometry, dict)
                    else {"type": "Point", "coordinates": [longitude, latitude]}
                )
                is_property_scope = (
                    isinstance(payload.get("metadata"), dict)
                    and payload["metadata"].get("scope") == "property"
                    and geometry.get("type") in {"Polygon", "MultiPolygon"}
                )
                observations.append(
                    Evidence(
                        source_type=SourceType.MIREYE,
                        source=base_source.model_copy(deep=True),
                        field_name=str(field_name),
                        value=value,
                        geometry=geometry,
                        semantic_scope=(
                            "property cultivated footprint"
                            if field_name == "cultivated_acres" and is_property_scope
                            else "provider physical field"
                        ),
                        confidence=0.75,
                        limitations=[
                            "Provider field context is physical evidence and does not establish legal rights."
                        ],
                        raw_reference={
                            "tool": provider_tool,
                            "arguments": args,
                            "provider_field": field_name,
                        },
                    )
                )
        return observations

    async def quote_request(
        self, latitude: float, longitude: float, fields: list[str]
    ) -> dict[str, Any]:
        """Not applicable for REST API — returns empty result."""
        return {"content": [], "note": "Quote requests are not available via the REST API."}

    async def fetch_batch_context(
        self, coordinates: list[tuple[float, float]], fields: list[str] | None = None
    ) -> list[ToolResult]:
        """Fetch context for multiple coordinates concurrently."""
        return list(
            await asyncio.gather(
                *(self.fetch_context(lat, lon, fields) for lat, lon in coordinates)
            )
        )

    async def fetch_context(
        self, latitude: float, longitude: float, fields: list[str] | None = None
    ) -> ToolResult:
        """Call POST /v1/fetch with the given coordinate and fields."""
        requested_fields = fields or _DEFAULT_FIELDS
        cache_key = (
            f"mireye:{latitude:.6f}:{longitude:.6f}:{','.join(sorted(requested_fields))}"
        )
        cached = provider_cache.get(cache_key)
        if cached:
            return cached

        if not self.settings.mireye_api_token:
            return ToolResult(
                tool_name="mireye.fetch_context",
                success=False,
                limitations=[
                    "MIREYE_API_TOKEN is not configured; set it in .env to enable Mireye physical context."
                ],
            )

        try:
            body: dict[str, Any] = {
                "lat": latitude,
                "lng": longitude,
                "fields": requested_fields,
            }
            async with async_client(timeout=120) as client:
                response = await client.post(
                    self._url("/v1/fetch"),
                    headers=self._headers(),
                    json=body,
                )
                response.raise_for_status()
                data = response.json()

            evidence = self._normalize_fetch_response(
                data, latitude, longitude, requested_fields
            )

            # Collect any partial failures as limitations
            limitations: list[str] = []
            for failure in data.get("partial_failures", []):
                field = failure.get("field", "unknown")
                error = failure.get("error", "unknown error")
                limitations.append(f"Mireye field '{field}' unavailable: {error}")

            result = ToolResult(
                tool_name="mireye.fetch_context",
                success=True,
                observations=evidence,
                limitations=limitations,
                raw_metadata={"api_endpoint": "/v1/fetch"},
            )
            provider_cache.set(cache_key, result)
            return result
        except Exception as exc:
            return ToolResult(
                tool_name="mireye.fetch_context",
                success=False,
                limitations=[f"Mireye unavailable: {exc}"],
            )


# Backward compatibility alias
MireyeMCPAdapter = MireyeRESTAdapter
