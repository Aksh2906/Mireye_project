from __future__ import annotations

from math import asin, cos, radians, sin, sqrt

from app.connectors.listing_providers import ListingProvider, ListingSearchCriteria
from app.domain.models import BuyerObjective, Geometry, PropertyAlternative


class OpportunityDiscoveryEngine:
    def __init__(self, provider: ListingProvider) -> None:
        self.provider = provider

    async def search(
        self,
        latitude: float,
        longitude: float,
        objective: BuyerObjective,
        initial_radius: float = 10,
    ) -> tuple[list[PropertyAlternative], list[float]]:
        maximum = objective.geography.max_distance_miles or max(50, initial_radius)
        radii = [
            radius
            for radius in dict.fromkeys(
                [initial_radius, max(25, initial_radius), max(50, initial_radius), maximum]
            )
            if radius <= maximum
        ]
        if not radii:
            radii = [maximum]
        searched: list[float] = []
        listing_by_key = {}
        for radius in radii:
            searched.append(radius)
            listings = await self.provider.search(
                ListingSearchCriteria(
                    latitude=latitude,
                    longitude=longitude,
                    radius_miles=radius,
                    price_max=objective.budget.acquisition_max,
                    acreage_min=objective.acreage.minimum,
                    acreage_max=objective.acreage.maximum,
                )
            )
            for listing in listings:
                key = listing.source_url.casefold().rstrip("/")
                listing_by_key[key] = listing
            if len(listing_by_key) >= 3:
                break
        alternatives = []
        for listing in listing_by_key.values():
            if listing.latitude is None or listing.longitude is None:
                continue
            distance = self._distance_miles(
                latitude, longitude, listing.latitude, listing.longitude
            )
            if distance > maximum:
                continue
            advantages: list[str] = []
            disadvantages: list[str] = []
            if listing.price is not None and objective.budget.acquisition_max is not None:
                (
                    advantages
                    if listing.price <= objective.budget.acquisition_max
                    else disadvantages
                ).append(
                    "Asking price is within the stated acquisition budget."
                    if listing.price <= objective.budget.acquisition_max
                    else "Asking price exceeds the stated acquisition budget."
                )
            if listing.acreage is not None and objective.acreage.minimum is not None:
                (
                    advantages if listing.acreage >= objective.acreage.minimum else disadvantages
                ).append(
                    "Listed acreage meets the stated minimum."
                    if listing.acreage >= objective.acreage.minimum
                    else "Listed acreage is below the stated minimum."
                )
            alternatives.append(
                PropertyAlternative(
                    source_listing_id=listing.id,
                    title=listing.title,
                    location=Geometry(coordinates=[listing.longitude, listing.latitude]),
                    price=listing.price,
                    acreage=listing.acreage,
                    source_url=listing.source_url,
                    distance_miles=round(distance, 1),
                    price_per_acre=(
                        round(listing.price / listing.acreage, 2)
                        if listing.price and listing.acreage
                        else None
                    ),
                    advantages=advantages,
                    disadvantages=disadvantages,
                    unknowns=[
                        "Agricultural fit, usable acreage, hazards, infrastructure, and economics require evidence-based investigation."
                    ],
                    evidence_quality=0.25,
                    investigation_depth="screened",
                )
            )
        alternatives.sort(
            key=lambda item: (
                len(item.disadvantages),
                item.price_per_acre if item.price_per_acre is not None else float("inf"),
                item.distance_miles if item.distance_miles is not None else float("inf"),
            )
        )
        for index, alternative in enumerate(alternatives):
            alternative.recommendation = "deep_analysis" if index < 3 else "screened"
            alternative.comparison_delta = round(
                max(0, 1 - len(alternative.disadvantages) * 0.25)
                + min(0.5, len(alternative.advantages) * 0.2),
                2,
            )
        return alternatives, searched

    @staticmethod
    def _distance_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        lat1r, lon1r, lat2r, lon2r = map(radians, (lat1, lon1, lat2, lon2))
        dlat, dlon = lat2r - lat1r, lon2r - lon1r
        value = sin(dlat / 2) ** 2 + cos(lat1r) * cos(lat2r) * sin(dlon / 2) ** 2
        return 3958.8 * 2 * asin(sqrt(value))
