from __future__ import annotations

from typing import Any, Protocol
from urllib.parse import quote

import httpx
from pydantic import BaseModel, Field

from app.config import get_settings
from app.connectors.http import async_client
from app.connectors.listing import ListingAdapter
from app.domain.models import Geometry


class ListingSearchCriteria(BaseModel):
    latitude: float | None = None
    longitude: float | None = None
    radius_miles: float = Field(default=10, gt=0)
    price_max: float | None = Field(default=None, gt=0)
    acreage_min: float | None = Field(default=None, gt=0)
    acreage_max: float | None = Field(default=None, gt=0)


class NormalizedListing(BaseModel):
    id: str
    source: str
    source_url: str
    title: str | None = None
    price: float | None = None
    acreage: float | None = None
    address: str | None = None
    city: str | None = None
    county: str | None = None
    state: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    description: str | None = None
    claimed_features: list[str] = Field(default_factory=list)
    geometry: Geometry | None = None
    images: list[str] = Field(default_factory=list)
    source_timestamp: str | None = None


class ListingProvider(Protocol):
    async def search(self, criteria: ListingSearchCriteria) -> list[NormalizedListing]: ...
    async def get_listing(self, listing_id: str) -> NormalizedListing | None: ...
    def normalize(self, raw: Any) -> NormalizedListing: ...


class GenericListingUrlAdapter:
    """URL ingestion only; it deliberately does not imply site-wide search permission."""

    def __init__(self) -> None:
        self.adapter = ListingAdapter()

    async def search(self, criteria: ListingSearchCriteria) -> list[NormalizedListing]:
        return []

    async def get_listing(self, listing_id: str) -> NormalizedListing | None:
        artifact, _ = await self.adapter.fetch(listing_id)
        if not artifact.raw_text:
            return None
        return NormalizedListing(
            id=listing_id,
            source=artifact.source or "url",
            source_url=listing_id,
            description=artifact.raw_text,
            price=artifact.asking_price,
            source_timestamp=artifact.retrieved_at.isoformat() if artifact.retrieved_at else None,
        )

    def normalize(self, raw: Any) -> NormalizedListing:
        return NormalizedListing.model_validate(raw)


class MockListingAdapter:
    def __init__(self, listings: list[NormalizedListing] | None = None) -> None:
        self.listings = {item.id: item for item in listings or []}

    async def search(self, criteria: ListingSearchCriteria) -> list[NormalizedListing]:
        results = list(self.listings.values())
        if criteria.price_max is not None:
            results = [
                item
                for item in results
                if item.price is not None and item.price <= criteria.price_max
            ]
        if criteria.acreage_min is not None:
            results = [
                item
                for item in results
                if item.acreage is not None and item.acreage >= criteria.acreage_min
            ]
        if criteria.acreage_max is not None:
            results = [
                item
                for item in results
                if item.acreage is not None and item.acreage <= criteria.acreage_max
            ]
        return results

    async def get_listing(self, listing_id: str) -> NormalizedListing | None:
        return self.listings.get(listing_id)

    def normalize(self, raw: Any) -> NormalizedListing:
        return NormalizedListing.model_validate(raw)


class _UnavailableDiscoveryAdapter(MockListingAdapter):
    """Contract placeholder until a permitted feed/API is configured."""

    async def search(self, criteria: ListingSearchCriteria) -> list[NormalizedListing]:
        return []


class LandWatchAdapter(_UnavailableDiscoveryAdapter):
    pass


class LandComAdapter(_UnavailableDiscoveryAdapter):
    pass


class ConfiguredListingAdapter:
    """Adapter for an explicitly configured, permitted JSON listing feed/API."""

    async def search(self, criteria: ListingSearchCriteria) -> list[NormalizedListing]:
        settings = get_settings()
        if not settings.listing_search_url:
            return []
        headers = (
            {"Authorization": f"Bearer {settings.listing_api_token}"}
            if settings.listing_api_token
            else {}
        )
        try:
            async with async_client(timeout=45) as client:
                response = await client.get(
                    settings.listing_search_url,
                    params=criteria.model_dump(exclude_none=True),
                    headers=headers,
                )
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, ValueError):
            return []
        rows = payload.get("listings", []) if isinstance(payload, dict) else payload
        if not isinstance(rows, list):
            return []
        normalized: list[NormalizedListing] = []
        for row in rows:
            try:
                normalized.append(self.normalize(row))
            except (TypeError, ValueError):
                continue
        return normalized

    async def get_listing(self, listing_id: str) -> NormalizedListing | None:
        matches = await self.search(ListingSearchCriteria())
        return next((item for item in matches if item.id == listing_id), None)

    def normalize(self, raw: Any) -> NormalizedListing:
        if not isinstance(raw, dict):
            raise TypeError("Listing payload must be an object")
        source_url = raw.get("source_url") or raw.get("url")
        listing_id = raw.get("id") or raw.get("listing_id") or source_url
        if not listing_id or not source_url:
            raise ValueError("Listing requires id and source URL")
        return NormalizedListing(
            id=str(listing_id),
            source=str(raw.get("source") or "Configured listing provider"),
            source_url=str(source_url),
            title=raw.get("title"),
            price=raw.get("price") or raw.get("asking_price"),
            acreage=raw.get("acreage") or raw.get("acres"),
            address=raw.get("address"),
            city=raw.get("city"),
            county=raw.get("county"),
            state=raw.get("state"),
            latitude=raw.get("latitude") or raw.get("lat"),
            longitude=raw.get("longitude") or raw.get("lon") or raw.get("lng"),
            description=raw.get("description"),
            claimed_features=raw.get("claimed_features") or raw.get("features") or [],
            geometry=raw.get("geometry"),
            images=raw.get("images") or [],
            source_timestamp=raw.get("source_timestamp") or raw.get("updated_at"),
        )


class RentCastListingAdapter:
    """Authorized RentCast sale-listing search normalized to the project contract."""

    async def search(self, criteria: ListingSearchCriteria) -> list[NormalizedListing]:
        settings = get_settings()
        if not settings.listing_search_url or not settings.listing_api_token:
            return []
        params: dict[str, Any] = {
            "latitude": criteria.latitude,
            "longitude": criteria.longitude,
            "radius": min(criteria.radius_miles, 100),
            "propertyType": "Land",
            "status": "Active",
            "limit": 100,
        }
        if criteria.price_max is not None:
            params["price"] = f"0:{criteria.price_max:g}"
        if criteria.acreage_min is not None or criteria.acreage_max is not None:
            minimum = round((criteria.acreage_min or 0) * 43560)
            maximum = (
                round(criteria.acreage_max * 43560) if criteria.acreage_max is not None else ""
            )
            params["lotSize"] = f"{minimum}:{maximum}"
        try:
            async with async_client(timeout=45) as client:
                response = await client.get(
                    settings.listing_search_url,
                    params={key: value for key, value in params.items() if value is not None},
                    headers={
                        "Accept": "application/json",
                        "X-Api-Key": settings.listing_api_token,
                    },
                )
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, ValueError):
            return []
        rows = payload.get("listings", []) if isinstance(payload, dict) else payload
        if not isinstance(rows, list):
            return []
        normalized: list[NormalizedListing] = []
        for row in rows:
            try:
                normalized.append(self.normalize(row))
            except (TypeError, ValueError):
                continue
        return normalized

    async def get_listing(self, listing_id: str) -> NormalizedListing | None:
        settings = get_settings()
        if not settings.listing_search_url or not settings.listing_api_token:
            return None
        url = f"{settings.listing_search_url.rstrip('/')}/{quote(listing_id, safe='')}"
        try:
            async with async_client(timeout=45) as client:
                response = await client.get(
                    url,
                    headers={
                        "Accept": "application/json",
                        "X-Api-Key": settings.listing_api_token,
                    },
                )
                if response.status_code == 404:
                    return None
                response.raise_for_status()
                return self.normalize(response.json())
        except (httpx.HTTPError, ValueError):
            return None

    def normalize(self, raw: Any) -> NormalizedListing:
        if not isinstance(raw, dict) or not raw.get("id"):
            raise ValueError("RentCast listing requires an id")
        latitude = _number_or_none(raw.get("latitude"))
        longitude = _number_or_none(raw.get("longitude"))
        lot_square_feet = _number_or_none(raw.get("lotSize"))
        acreage = lot_square_feet / 43560 if lot_square_feet is not None else None
        provider_url = f"https://api.rentcast.io/v1/listings/sale/{quote(str(raw['id']), safe='')}"
        attributes = [
            f"Property type: {raw['propertyType']}" if raw.get("propertyType") else None,
            f"Listing status: {raw['status']}" if raw.get("status") else None,
            f"MLS: {raw['mlsName']} #{raw.get('mlsNumber', '')}" if raw.get("mlsName") else None,
        ]
        address = raw.get("formattedAddress") or raw.get("addressLine1")
        return NormalizedListing(
            id=str(raw["id"]),
            source="RentCast sale listings",
            source_url=provider_url,
            title=address or "Land listing",
            price=_number_or_none(raw.get("price")),
            acreage=round(acreage, 2) if acreage is not None else None,
            address=address,
            city=raw.get("city"),
            county=raw.get("county"),
            state=raw.get("state"),
            latitude=latitude,
            longitude=longitude,
            description=(
                f"{raw.get('propertyType', 'Property')} listed as {raw.get('status', 'unknown status')}; "
                f"{raw.get('daysOnMarket', 'unknown')} days on market."
            ),
            claimed_features=[item for item in attributes if item],
            geometry=Geometry(type="Point", coordinates=[longitude, latitude])
            if latitude is not None and longitude is not None
            else None,
            source_timestamp=raw.get("lastSeenDate") or raw.get("listedDate"),
        )


def _number_or_none(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def configured_listing_provider() -> ListingProvider:
    settings = get_settings()
    if not settings.listing_search_url:
        return _UnavailableDiscoveryAdapter()
    if "api.rentcast.io" in settings.listing_search_url.casefold():
        return RentCastListingAdapter()
    return ConfiguredListingAdapter()
