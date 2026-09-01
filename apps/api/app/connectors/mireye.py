from __future__ import annotations

import asyncio
import json
from typing import Any
from uuid import uuid4

from app.config import get_settings
from app.connectors.cache import provider_cache
from app.connectors.http import async_client
from app.domain.models import Evidence, EvidenceSource, SourceType, ToolResult

MIREYE_HAZARD_FIELDS = [
    "fema_flood_zone",
    "within_floodplain_polygon",
    "intersects_wetland",
    "wetland_acres",
    "soil_ponding_frequency_class",
    "wildfire_annual_frequency",
    "tornado_annual_frequency",
    "hail_annual_frequency",
    "lightning_annual_flash_days",
    "landslide_susceptibility_index",
    "soil_shrink_swell_class",
    "fire_hazard_severity_zone_class",
    "most_recent_burn_year",
    "design_wind_speed_mph",
    "seismic_pga_2pct_50yr_g",
    "seismic_design_category",
]

MIREYE_LAND_USE_FIELDS = [
    "parcel_boundary_geojson",
    "slope_degrees",
    "soil_drainage_class",
    "soil_hydrologic_group",
    "soil_available_water_capacity",
    "land_use_class",
    "lcms_class",
    "cdl_class",
    "dominant_crop_5y",
    "tree_canopy_pct",
    "within_water_service_area",
    "nearest_water_service_area_distance_m",
    "domestic_well_households_per_km2",
    "nearest_major_road_distance_m",
    "roads_within_500m_count",
    "electric_utility_service_territory",
    "avg_retail_electricity_price_industrial_usd_per_kwh",
    "within_sewer_service_area",
    "nearest_wastewater_plant_distance_m",
    "primary_building_footprint_sqm",
    "nearest_grocery_store_distance_m",
    "nearest_restaurant_distance_m",
    "nearest_urban_area_distance_m",
    "housing_units_within_1km",
    "ghi_annual_kwh_m2_day",
    "pv_capacity_factor_pct",
    "pv_specific_yield_kwh_per_kw",
    "nearest_utility_solar_facility_distance_m",
    "nearest_utility_solar_facility_capacity_mw",
    "nearest_transmission_line_distance_m",
    "mean_wind_speed_100m_ms",
    "wind_capacity_factor_pct",
    "wind_least_cost_interconnect_distance_m",
    "nearest_airport_distance_m",
]


class MireyeMCPAdapter:
    """A provider-isolated MCP Streamable HTTP adapter with runtime tool discovery."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._tools: list[dict[str, Any]] | None = None
        self._session_id: str | None = None

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
        }
        token = self.settings.mireye_api_token or self.settings.mireye_mcp_token
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if self._session_id:
            headers["Mcp-Session-Id"] = self._session_id
        return headers

    async def _rpc(self, method: str, params: dict[str, Any] | None = None) -> Any:
        if not self.settings.mireye_mcp_url:
            raise RuntimeError("MIREYE_MCP_URL is not configured")
        body = {"jsonrpc": "2.0", "id": str(uuid4()), "method": method, "params": params or {}}
        async with async_client(timeout=120) as client:
            response = await client.post(
                self.settings.mireye_mcp_url, headers=self._headers(), json=body
            )
            response.raise_for_status()
            if response.headers.get("mcp-session-id"):
                self._session_id = response.headers["mcp-session-id"]
            payload = response.json()
        if payload.get("error"):
            raise RuntimeError(payload["error"].get("message", "MCP request failed"))
        return payload.get("result", {})

    async def discover_tools(self) -> list[dict[str, Any]]:
        if self._tools is not None:
            return self._tools
        try:
            await self._rpc(
                "initialize",
                {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "mireye-agri-agent", "version": "0.1.0"},
                },
            )
            result = await self._rpc("tools/list")
            self._tools = result.get("tools", [])
        except Exception:
            self._tools = []
            raise
        return self._tools

    async def _select_tool(self, concepts: tuple[str, ...]) -> dict[str, Any]:
        tools = await self.discover_tools()
        for tool in tools:
            haystack = f"{tool.get('name', '')} {tool.get('description', '')}".lower()
            if all(concept in haystack for concept in concepts):
                return tool
        raise RuntimeError(f"Mireye MCP exposes no matching tool for: {', '.join(concepts)}")

    async def get_field_catalog(self) -> list[dict[str, Any]]:
        tool = await self._select_tool(("field",))
        result = await self._rpc("tools/call", {"name": tool["name"], "arguments": {}})
        return result.get("content", [])

    @staticmethod
    def _structured_payload(result: dict[str, Any]) -> Any:
        if "structuredContent" in result:
            return result["structuredContent"]
        content = result.get("content", [])
        text_items: list[str] = []
        for item in content if isinstance(content, list) else []:
            if isinstance(item, dict) and item.get("type") == "text":
                text = item.get("text", "")
                try:
                    return json.loads(text)
                except (TypeError, json.JSONDecodeError):
                    if isinstance(text, str) and text:
                        text_items.append(text)
        if text_items:
            return "\n\n".join(text_items)
        return content

    def _normalize_rest_answer(
        self, payload: dict[str, Any], latitude: float, longitude: float
    ) -> list[Evidence]:
        if not self.settings.mireye_api_url:
            raise RuntimeError("MIREYE_API_URL is not configured")
        answer = payload.get("answer") or payload.get("response") or payload.get("result")
        # The hosted endpoint can wrap its structured response as JSON inside
        # the answer string. Decode that envelope for the readable evidence UI.
        if isinstance(answer, str) and answer.lstrip().startswith(("{", "[")):
            try:
                answer = json.loads(answer)
            except json.JSONDecodeError:
                pass
        if not isinstance(answer, (dict, list)) and (
            not isinstance(answer, str) or not answer.strip()
        ):
            answer = {
                "status": "Source-backed context returned without a synthesized narrative.",
                "answer": "",
                "fields_used": payload.get("fields_used", []),
                "citations": payload.get("citations", []),
                "data_gaps": payload.get("data_gaps", []),
                "resolved_location": payload.get("resolved_location"),
            }
        response_payload = answer if isinstance(answer, dict) else payload
        confidence_value = response_payload.get("confidence", payload.get("confidence", 0.75))
        if isinstance(confidence_value, str):
            confidence = {"high": 0.85, "medium": 0.7, "low": 0.5}.get(
                confidence_value.lower(), 0.7
            )
        else:
            try:
                confidence = min(1.0, max(0.0, float(confidence_value)))
            except (TypeError, ValueError):
                confidence = 0.7
        source_url = f"{self.settings.mireye_api_url.rstrip('/')}/v1/ask"
        return [
            Evidence(
                source_type=SourceType.MIREYE,
                source=EvidenceSource(
                    publisher="Mireye", dataset="Property Intelligence", url=source_url
                ),
                field_name="mireye_report",
                value=answer,
                geometry={"type": "Point", "coordinates": [longitude, latitude]},
                semantic_scope="physical context at requested coordinate",
                confidence=confidence,
                limitations=[
                    "Point context does not establish a legal parcel boundary or property right."
                ],
                raw_reference={
                    "endpoint": "/v1/ask",
                    "citations": response_payload.get("citations", []),
                    "fields_used": response_payload.get("fields_used", []),
                    "trace": response_payload.get("trace"),
                },
            )
        ]

    async def _fetch_rest_context(
        self, latitude: float, longitude: float, fields: list[str] | None
    ) -> list[Evidence]:
        if not self.settings.mireye_api_url:
            raise RuntimeError("MIREYE_API_URL is not configured")
        question = (
            "For agricultural land acquisition diligence, report observed values for "
            "terrain, soils and drainage; FEMA flood zone and floodplain intersection; "
            "wetlands and ponding; drought, wildfire, extreme heat or cold, severe storm, "
            "hail, tornado, erosion, and landslide exposure; land cover or crops; access; "
            "and parcel or boundary context. Separate observed values from unavailable "
            "fields, cite every source, and do not infer legal rights or interpret missing "
            "hazard data as no exposure."
        )
        if fields:
            question += f" Prioritize these fields: {', '.join(fields)}."
        body = {
            "lat": latitude,
            "lng": longitude,
            "question": question,
            "include_trace": True,
        }
        # Mireye documents /v1/ask as an LLM-backed call that may take up to 110 seconds.
        async with async_client(timeout=120) as client:
            response = await client.post(
                f"{self.settings.mireye_api_url.rstrip('/')}/v1/ask",
                headers=self._headers(),
                json=body,
            )
            response.raise_for_status()
            payload = response.json()
        if not isinstance(payload, dict):
            raise TypeError("Mireye returned an unexpected response")
        return self._normalize_rest_answer(payload, latitude, longitude)

    def _normalize_context(
        self,
        provider_tool: str,
        args: dict[str, Any],
        result: dict[str, Any],
        latitude: float,
        longitude: float,
    ) -> list[Evidence]:
        payload = self._structured_payload(result)
        base_source = EvidenceSource(
            publisher="Mireye",
            dataset=provider_tool,
            url=self.settings.mireye_mcp_url,
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

    def _normalize_fetch_payload(
        self, payload: dict[str, Any], latitude: float, longitude: float
    ) -> tuple[list[Evidence], list[str]]:
        """Normalize deterministic /v1/fetch fields without hiding partial failures."""
        observations: list[Evidence] = []
        limitations: list[str] = []
        fields = payload.get("fields", {})
        if not isinstance(fields, dict):
            raise TypeError("Mireye /v1/fetch returned no field map")
        confidence_map = {"high": 0.9, "medium": 0.7, "low": 0.45, "unknown": 0.35}
        mireye_api_url = self.settings.mireye_api_url or ""
        endpoint = f"{mireye_api_url.rstrip('/')}/v1/fetch"
        for field_name, record in fields.items():
            if not isinstance(record, dict):
                record = {"value": record, "status": "ok"}
            if record.get("status") == "failed" or record.get("error"):
                limitations.append(
                    f"Mireye field {field_name} unavailable: {record.get('error') or 'provider reported failure'}"
                )
                continue
            value = record.get("value")
            if value is None:
                limitations.append(f"Mireye field {field_name} returned no value.")
                continue
            source_name = str(record.get("source") or "Mireye curated source")
            geometry: dict[str, Any] = {"type": "Point", "coordinates": [longitude, latitude]}
            if field_name in {"parcel_boundary_geojson", "parcel_geometry"} and isinstance(
                value, dict
            ):
                candidate = value.get("geometry") if value.get("type") == "Feature" else value
                if isinstance(candidate, dict) and candidate.get("type"):
                    geometry = candidate
            notes = record.get("notes")
            field_limitations = [
                "Coordinate-level provider result; verify parcel coverage before treating it as whole-property evidence."
            ]
            if notes:
                field_limitations.append(str(notes))
            confidence_label = str(record.get("confidence") or "unknown").casefold()
            observations.append(
                Evidence(
                    source_type=SourceType.MIREYE,
                    source=EvidenceSource(
                        publisher="Mireye",
                        dataset=source_name,
                        url=record.get("source_url") or endpoint,
                        vintage=str(record["dataset_vintage"])
                        if record.get("dataset_vintage") is not None
                        else None,
                    ),
                    field_name=str(field_name),
                    value=value,
                    unit=record.get("unit"),
                    geometry=geometry,
                    semantic_scope="Mireye deterministic field at requested coordinate",
                    confidence=confidence_map.get(confidence_label, 0.55),
                    limitations=field_limitations,
                    raw_reference={
                        "endpoint": "/v1/fetch",
                        "provider_field": field_name,
                        "status": record.get("status", "ok"),
                        "fetched_at": record.get("fetched_at") or payload.get("fetched_at"),
                        "resolved_location": payload.get("resolved_location"),
                    },
                )
            )
        for failure in payload.get("partial_failures", []) or []:
            text = failure if isinstance(failure, str) else json.dumps(failure, default=str)
            if text not in limitations:
                limitations.append(f"Mireye partial failure: {text}")
        return observations, limitations

    async def fetch_fields(
        self,
        latitude: float,
        longitude: float,
        fields: list[str] | None = None,
        preset: str | None = None,
    ) -> ToolResult:
        """Fetch source-backed, deterministic Mireye fields through REST v1/fetch."""
        requested = sorted(dict.fromkeys(fields or []))
        cache_key = (
            f"mireye-fetch:{latitude:.6f}:{longitude:.6f}:{preset or ''}:{','.join(requested)}"
        )
        cached = provider_cache.get(cache_key)
        if cached:
            return cached
        if not self.settings.mireye_api_url:
            return ToolResult(
                tool_name="mireye.fetch_fields",
                success=False,
                limitations=["MIREYE_API_URL is not configured."],
            )
        body: dict[str, Any] = {"lat": latitude, "lng": longitude}
        if requested:
            body["fields"] = requested
        elif preset:
            body["preset"] = preset
        else:
            return ToolResult(
                tool_name="mireye.fetch_fields",
                success=False,
                limitations=["At least one Mireye field or preset is required."],
            )
        try:
            async with async_client(timeout=90) as client:
                response = await client.post(
                    f"{self.settings.mireye_api_url.rstrip('/')}/v1/fetch",
                    headers=self._headers(),
                    json=body,
                )
                response.raise_for_status()
                payload = response.json()
            if not isinstance(payload, dict):
                raise TypeError("Mireye returned an unexpected /v1/fetch response")
            observations, limitations = self._normalize_fetch_payload(payload, latitude, longitude)
            result = ToolResult(
                tool_name="mireye.fetch_fields",
                success=bool(observations),
                observations=observations,
                limitations=limitations,
                raw_metadata={
                    "provider_endpoint": "/v1/fetch",
                    "requested_fields": requested,
                    "preset": preset,
                },
            )
            provider_cache.set(cache_key, result)
            return result
        except Exception as exc:
            return ToolResult(
                tool_name="mireye.fetch_fields",
                success=False,
                limitations=[f"Mireye /v1/fetch unavailable: {exc}"],
            )

    async def quote_request(
        self, latitude: float, longitude: float, fields: list[str]
    ) -> dict[str, Any]:
        tool = await self._select_tool(("quote",))
        schema = tool.get("inputSchema", {}).get("properties", {})
        args: dict[str, Any] = {}
        for aliases, value in (
            (("latitude", "lat"), latitude),
            (("longitude", "lon", "lng"), longitude),
            (("fields",), fields),
        ):
            key = next((candidate for candidate in aliases if candidate in schema), None)
            if key:
                args[key] = value
        return await self._rpc("tools/call", {"name": tool["name"], "arguments": args})

    async def fetch_batch_context(
        self, coordinates: list[tuple[float, float]], fields: list[str] | None = None
    ) -> list[ToolResult]:
        try:
            tool = await self._select_tool(("batch", "context"))
            schema = tool.get("inputSchema", {}).get("properties", {})
            args: dict[str, Any] = {}
            points = [{"latitude": lat, "longitude": lon} for lat, lon in coordinates]
            for key in ("coordinates", "points", "locations"):
                if key in schema:
                    args[key] = points
                    break
            if fields and "fields" in schema:
                args["fields"] = fields
            raw = await self._rpc("tools/call", {"name": tool["name"], "arguments": args})
            payload = self._structured_payload(raw)
            if not isinstance(payload, list) or len(payload) != len(coordinates):
                raise RuntimeError(
                    "Mireye batch result could not be aligned to requested coordinates"
                )
            results: list[ToolResult] = []
            for (latitude, longitude), item in zip(coordinates, payload):
                normalized = self._normalize_context(
                    tool["name"], args, {"structuredContent": item}, latitude, longitude
                )
                results.append(
                    ToolResult(
                        tool_name="mireye.fetch_batch_context",
                        success=True,
                        observations=normalized,
                        raw_metadata={"provider_tool": tool["name"]},
                    )
                )
            return results
        except Exception:
            return await asyncio.gather(
                *(self.fetch_context(lat, lon, fields) for lat, lon in coordinates)
            )

    async def fetch_context(
        self, latitude: float, longitude: float, fields: list[str] | None = None
    ) -> ToolResult:
        cache_key = f"mireye:{latitude:.6f}:{longitude:.6f}:{','.join(sorted(fields or []))}"
        cached = provider_cache.get(cache_key)
        if cached:
            return cached
        try:
            if self.settings.mireye_api_url:
                evidence = await self._fetch_rest_context(latitude, longitude, fields)
                result = ToolResult(
                    tool_name="mireye.fetch_context",
                    success=True,
                    observations=evidence,
                    raw_metadata={"provider_endpoint": "/v1/ask"},
                )
                provider_cache.set(cache_key, result)
                return result

            try:
                tool = await self._select_tool(("fetch",))
            except RuntimeError:
                tool = await self._select_tool(("ask",))
            schema = tool.get("inputSchema", {}).get("properties", {})
            args: dict[str, Any] = {}
            for candidate in ("latitude", "lat"):
                if candidate in schema:
                    args[candidate] = latitude
                    break
            for candidate in ("longitude", "lon", "lng"):
                if candidate in schema:
                    args[candidate] = longitude
                    break
            if fields and "fields" in schema:
                args["fields"] = fields
            if "question" in schema:
                args["question"] = (
                    "Summarize agricultural property context, limitations, and sources "
                    "for acquisition diligence. Return Markdown when appropriate."
                )
            result = await self._rpc("tools/call", {"name": tool["name"], "arguments": args})
            evidence = self._normalize_context(tool["name"], args, result, latitude, longitude)
            result = ToolResult(
                tool_name="mireye.fetch_context",
                success=True,
                observations=evidence,
                raw_metadata={"provider_tool": tool["name"]},
            )
            provider_cache.set(cache_key, result)
            return result
        except Exception as exc:
            return ToolResult(
                tool_name="mireye.fetch_context",
                success=False,
                limitations=[f"Mireye unavailable: {exc}"],
            )
