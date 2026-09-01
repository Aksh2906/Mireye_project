from __future__ import annotations

from math import sqrt
from typing import Any

from pyproj import Geod

from app.config import get_settings
from app.connectors.http import async_client
from app.domain.models import BoundaryKind, BoundaryRecord, Geometry, InvestigationState


class BoundaryValidationError(ValueError):
    pass


class BoundaryService:
    geod = Geod(ellps="WGS84")

    def validate(self, geometry: dict[str, Any]) -> dict[str, Any]:
        geometry_type = geometry.get("type")
        coordinates = geometry.get("coordinates")
        if geometry_type not in {"Polygon", "MultiPolygon"} or not isinstance(coordinates, list):
            raise BoundaryValidationError("Boundary must be a GeoJSON Polygon or MultiPolygon")
        polygons = coordinates if geometry_type == "MultiPolygon" else [coordinates]
        total_square_meters = 0.0
        normalized: list[list[list[list[float]]]] = []
        for polygon in polygons:
            if not polygon or not isinstance(polygon[0], list) or len(polygon[0]) < 3:
                raise BoundaryValidationError(
                    "Boundary exterior ring requires at least three points"
                )
            rings: list[list[list[float]]] = []
            for ring in polygon:
                if ring[0] != ring[-1]:
                    ring = [*ring, ring[0]]
                if any(
                    not isinstance(point, list)
                    or len(point) < 2
                    or not -180 <= point[0] <= 180
                    or not -90 <= point[1] <= 90
                    for point in ring
                ):
                    raise BoundaryValidationError("Boundary contains an invalid coordinate")
                longitude, latitude = zip(*[(point[0], point[1]) for point in ring])
                area, _ = self.geod.polygon_area_perimeter(longitude, latitude)
                total_square_meters += abs(area) if not rings else -abs(area)
                rings.append(ring)
            normalized.append(rings)
        normalized_geometry = {
            "type": geometry_type,
            "coordinates": normalized if geometry_type == "MultiPolygon" else normalized[0],
        }
        return {
            "geometry": normalized_geometry,
            "area_acres": round(max(0, total_square_meters) / 4046.8564224, 2),
            "boundary_kind": "analysis geometry",
            "is_legal_boundary": False,
        }

    def build_record(
        self,
        geometry: dict[str, Any],
        *,
        kind: BoundaryKind,
        source_name: str,
        source_url: str | None = None,
        claimed_acres: float | None = None,
        confidence: float = 0.6,
        limitations: list[str] | None = None,
    ) -> BoundaryRecord:
        validated = self.validate(geometry)
        area = float(validated["area_acres"])
        difference = area - claimed_acres if claimed_acres else None
        difference_percent = (
            difference / claimed_acres if claimed_acres and difference is not None else None
        )
        is_authoritative = kind == BoundaryKind.AUTHORITATIVE_PARCEL
        default_limit = (
            "Parcel geometry is an assessor/GIS record and is not a legal survey."
            if is_authoritative
            else "Analysis geometry is not a legal survey or ownership determination."
        )
        return BoundaryRecord(
            geometry=Geometry.model_validate(validated["geometry"]),
            kind=kind,
            source_name=source_name,
            source_url=source_url,
            confidence=confidence,
            area_acres=area,
            claimed_acres=claimed_acres,
            acreage_difference=round(difference, 2) if difference is not None else None,
            acreage_difference_percent=(
                round(difference_percent, 4) if difference_percent is not None else None
            ),
            is_legal_boundary=False,
            limitations=list(dict.fromkeys([*(limitations or []), default_limit])),
        )

    def resolve_from_state(self, state: InvestigationState) -> BoundaryRecord | None:
        if state.boundary:
            return state.boundary
        candidates = [
            item
            for item in state.evidence
            if item.geometry and item.geometry.get("type") in {"Polygon", "MultiPolygon"}
        ]
        priority = {
            "listing": 0,
            "parcel": 1,
            "property boundary": 2,
            "property cultivated footprint": 3,
        }
        candidates.sort(
            key=lambda item: priority.get(
                str(
                    item.raw_reference.get("boundary_source") or item.semantic_scope or ""
                ).casefold(),
                9,
            )
        )
        for item in candidates:
            scope = str(
                item.raw_reference.get("boundary_source") or item.semantic_scope or ""
            ).casefold()
            kind = (
                BoundaryKind.LISTING
                if "listing" in scope
                else BoundaryKind.AUTHORITATIVE_PARCEL
                if "parcel" in scope
                else BoundaryKind.ANALYSIS
            )
            try:
                return self.build_record(
                    item.geometry or {},
                    kind=kind,
                    source_name=f"{item.source.publisher} — {item.source.dataset}",
                    source_url=item.source.url,
                    claimed_acres=state.property.acreage if state.property else None,
                    confidence=item.confidence,
                    limitations=item.limitations,
                )
            except BoundaryValidationError:
                continue
        return None

    def generate_analysis_geometry(
        self,
        latitude: float,
        longitude: float,
        acreage: float,
    ) -> BoundaryRecord:
        side_meters = sqrt(acreage * 4046.8564224)
        corner_distance = side_meters / sqrt(2)
        corners = [
            list(self.geod.fwd(longitude, latitude, bearing, corner_distance)[:2])
            for bearing in (315, 45, 135, 225)
        ]
        geometry = {"type": "Polygon", "coordinates": [[*corners, corners[0]]]}
        return self.build_record(
            geometry,
            kind=BoundaryKind.ANALYSIS,
            source_name="Generated acreage-equivalent analysis area",
            claimed_acres=acreage,
            confidence=0.25,
            limitations=[
                "This square is centered on the resolved point and sized to the claimed acreage.",
                "It does not indicate parcel location, shape, ownership, cultivation, or legal limits.",
            ],
        )


class ParcelAdapter:
    """Permission-safe adapter for a configured parcel lookup endpoint."""

    async def lookup(self, latitude: float, longitude: float) -> dict[str, Any] | None:
        settings = get_settings()
        if not settings.parcel_api_url:
            return None
        headers = (
            {"Authorization": f"Bearer {settings.parcel_api_token}"}
            if settings.parcel_api_token
            else {}
        )
        async with async_client(timeout=45) as client:
            response = await client.get(
                settings.parcel_api_url,
                params={"latitude": latitude, "longitude": longitude},
                headers=headers,
            )
            response.raise_for_status()
            payload = response.json()
        geometry = payload.get("geometry") if isinstance(payload, dict) else None
        if not isinstance(geometry, dict):
            return None
        return payload
