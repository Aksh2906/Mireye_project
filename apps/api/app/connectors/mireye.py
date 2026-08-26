from __future__ import annotations

import asyncio
import json
from typing import Any
from uuid import uuid4

from app.config import get_settings
from app.connectors.cache import provider_cache
from app.connectors.http import async_client
from app.domain.models import Evidence, EvidenceSource, SourceType, ToolResult


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
        async with async_client(timeout=60) as client:
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
        if not isinstance(answer, str):
            answer = json.dumps(payload, default=str)
        confidence_value = payload.get("confidence", 0.75)
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
                    "citations": payload.get("citations", []),
                    "fields_used": payload.get("fields_used", []),
                    "trace": payload.get("trace"),
                },
            )
        ]

    async def _fetch_rest_context(
        self, latitude: float, longitude: float, fields: list[str] | None
    ) -> list[Evidence]:
        if not self.settings.mireye_api_url:
            raise RuntimeError("MIREYE_API_URL is not configured")
        question = (
            "For agricultural land acquisition diligence, summarize terrain, soils and "
            "drainage, flood or wetland exposure, land cover or crops, access, and parcel "
            "or boundary context. Clearly state missing data, cite sources, and do not "
            "infer legal rights."
        )
        if fields:
            question += f" Prioritize these fields: {', '.join(fields)}."
        body = {
            "lat": latitude,
            "lng": longitude,
            "question": question,
            "include_trace": True,
        }
        async with async_client(timeout=60) as client:
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
