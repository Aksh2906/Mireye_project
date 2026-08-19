from app.config import get_settings
from app.connectors.cache import geocode_cache
from app.connectors.http import async_client
from app.domain.models import Evidence, EvidenceSource, Geometry, Property, SourceType


class Geocoder:
    async def resolve(self, address: str) -> tuple[Property | None, list[Evidence], list[str]]:
        cache_key = f"geocode:{address.strip().lower()}"
        cached = geocode_cache.get(cache_key)
        if cached:
            return cached
        settings = get_settings()
        try:
            async with async_client() as client:
                response = await client.get(
                    f"{settings.geocoder_base_url.rstrip('/')}/search",
                    params={"q": address, "format": "jsonv2", "addressdetails": 1, "limit": 1},
                )
                response.raise_for_status()
                rows = response.json()
        except Exception as exc:
            return None, [], [f"Geocoding unavailable: {type(exc).__name__}"]
        if not rows:
            return None, [], ["No geocoding result matched the supplied property description."]
        row = rows[0]
        parts = row.get("address", {})
        latitude, longitude = float(row["lat"]), float(row["lon"])
        geometry = Geometry(type="Point", coordinates=[longitude, latitude])
        prop = Property(
            address=row.get("display_name", address),
            latitude=latitude,
            longitude=longitude,
            state=parts.get("state"),
            county=parts.get("county"),
            geometry=geometry,
        )
        evidence = Evidence(
            source_type=SourceType.GEOCODER,
            source=EvidenceSource(
                publisher="OpenStreetMap contributors",
                dataset="Nominatim",
                url=settings.geocoder_base_url,
            ),
            field_name="resolved_location",
            value={"display_name": prop.address, "lat": latitude, "lon": longitude},
            geometry=geometry.model_dump(),
            semantic_scope="address geocoding",
            confidence=float(row.get("importance", 0.5)),
            limitations=["Geocoding identifies a location, not a verified legal parcel boundary."],
            raw_reference={
                "place_id": row.get("place_id"),
                "osm_type": row.get("osm_type"),
                "osm_id": row.get("osm_id"),
            },
        )
        result: tuple[Property | None, list[Evidence], list[str]] = (prop, [evidence], [])
        geocode_cache.set(cache_key, result)
        return result
