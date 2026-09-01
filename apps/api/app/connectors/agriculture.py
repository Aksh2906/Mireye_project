from __future__ import annotations

import re
from datetime import UTC, datetime

from pyproj import Transformer

from app.config import get_settings
from app.connectors.http import async_client
from app.domain.models import Evidence, EvidenceSource, SourceType, ToolResult

NON_AGRICULTURAL_CDL_CATEGORIES = {
    "background",
    "clouds/no data",
    "developed/open space",
    "developed/low intensity",
    "developed/med intensity",
    "developed/medium intensity",
    "developed/high intensity",
    "open water",
    "deciduous forest",
    "evergreen forest",
    "mixed forest",
    "shrubland",
    "barren",
    "woody wetlands",
    "herbaceous wetlands",
    "aquaculture",
}


def is_agricultural_category(category: str) -> bool:
    normalized = category.strip().casefold()
    return (
        bool(normalized)
        and normalized not in NON_AGRICULTURAL_CDL_CATEGORIES
        and not normalized.startswith("developed/")
    )


def parse_cdl_result(payload: str) -> dict[str, object] | None:
    result = re.search(r"<Result>\s*\{(.+?)\}\s*</Result>", payload, re.IGNORECASE)
    if not result:
        return None
    body = result.group(1)
    code_match = re.search(r"\bvalue\s*:\s*(-?\d+)", body, re.IGNORECASE)
    category_match = re.search(r'\bcategory\s*:\s*"([^"]+)"', body, re.IGNORECASE)
    if not code_match:
        return None
    category = category_match.group(1).strip() if category_match else "Unknown class"
    agricultural = is_agricultural_category(category)
    return {"code": int(code_match.group(1)), "category": category, "is_agricultural": agricultural}


class AgricultureAdapter:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def get_crop_history(
        self, latitude: float, longitude: float, years: list[int]
    ) -> ToolResult:
        observations: list[Evidence] = []
        limitations: list[str] = []
        x, y = Transformer.from_crs("EPSG:4326", "EPSG:5070", always_xy=True).transform(
            longitude, latitude
        )
        async with async_client(timeout=45) as client:
            for year in years:
                try:
                    response = await client.get(
                        self.settings.cdl_service_url,
                        params={"year": year, "x": x, "y": y},
                    )
                    response.raise_for_status()
                    observation = parse_cdl_result(response.text)
                    if not observation:
                        limitations.append(f"CDL {year} returned no interpretable observation.")
                        continue
                    observations.append(
                        Evidence(
                            source_type=SourceType.USDA_CDL,
                            source=EvidenceSource(
                                publisher="USDA NASS",
                                dataset="Cropland Data Layer",
                                url=self.settings.cdl_service_url,
                                vintage=str(year),
                            ),
                            field_name="crop_class",
                            value=observation,
                            geometry={"type": "Point", "coordinates": [longitude, latitude]},
                            spatial_resolution="raster cell (dataset-year dependent)",
                            temporal_resolution="annual",
                            semantic_scope="observed land-cover classification",
                            confidence=0.7,
                            limitations=[
                                "CDL is a classified raster proxy, not a survey of legal or tillable acreage."
                            ],
                            raw_reference={
                                "request_crs": "EPSG:5070",
                                "x": x,
                                "y": y,
                                "response_excerpt": response.text[:500],
                            },
                        )
                    )
                except Exception as exc:
                    limitations.append(f"CDL {year} unavailable: {type(exc).__name__}")
        return ToolResult(
            tool_name="agriculture.get_crop_history",
            success=bool(observations),
            observations=observations,
            limitations=limitations,
        )

    async def get_soil_context(self, latitude: float, longitude: float) -> ToolResult:
        query = (
            "SELECT TOP 25 muname, mu.mukey, drainagecl, hydgrp, farmlndcl "
            "FROM mapunit mu LEFT JOIN component co ON mu.mukey=co.mukey "
            f"WHERE mu.mukey IN (SELECT mukey FROM "
            f"SDA_Get_Mukey_from_intersection_with_WktWgs84('POINT({longitude} {latitude})'))"
        )
        try:
            async with async_client(timeout=45) as client:
                response = await client.post(
                    self.settings.ssurgo_service_url,
                    data={"query": query, "format": "JSON+COLUMNNAME"},
                )
                response.raise_for_status()
                data = response.json()
            evidence = Evidence(
                source_type=SourceType.USDA_SSURGO,
                source=EvidenceSource(
                    publisher="USDA NRCS",
                    dataset="Soil Data Access / SSURGO",
                    url=self.settings.ssurgo_service_url,
                ),
                field_name="soil_context",
                value=data.get("Table", []),
                geometry={"type": "Point", "coordinates": [longitude, latitude]},
                semantic_scope="mapped soil component context",
                confidence=0.7,
                limitations=[
                    "Mapped soil context can contain multiple components and requires field verification."
                ],
                raw_reference={
                    "query_hash": str(abs(hash(query))),
                    "retrieved_year": datetime.now(UTC).year,
                },
            )
            return ToolResult(
                tool_name="agriculture.get_soil_context", success=True, observations=[evidence]
            )
        except Exception as exc:
            return ToolResult(
                tool_name="agriculture.get_soil_context",
                success=False,
                limitations=[f"SSURGO unavailable: {type(exc).__name__}"],
            )
