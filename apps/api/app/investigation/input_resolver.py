from __future__ import annotations

import re

from app.connectors.geocoder import Geocoder
from app.connectors.listing import ListingAdapter
from app.domain.models import (
    Claim,
    Evidence,
    EvidenceSource,
    InputType,
    InvestigationState,
    ListingArtifact,
    Property,
    SourceType,
)

ACRE_PATTERN = re.compile(r"\b([\d,]+(?:\.\d+)?)\s*(?:-|\s)?acres?\b", re.IGNORECASE)
PRICE_PATTERN = re.compile(
    r"(?:\$\s*([\d,.]+)\s*([mk])?\b|\blisted\s+(?:at|for)\s+([\d,.]+)\s*([mk])?)", re.IGNORECASE
)
CLAIM_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("tillable_acres", re.compile(r"\b([\d,.]+)\s+acres?\s+(?:are\s+)?tillable\b", re.IGNORECASE)),
    ("drainage", re.compile(r"\b(?:excellent|good|well[- ]drained)\s+drainage\b", re.IGNORECASE)),
    (
        "irrigation",
        re.compile(r"\b(?:irrigated|irrigation available|center pivot)\b", re.IGNORECASE),
    ),
    ("soil_quality", re.compile(r"\b(?:productive|excellent|prime)\s+soils?\b", re.IGNORECASE)),
    ("flood", re.compile(r"\b(?:no|minimal|low)\s+flood(?:ing| risk| issues?)\b", re.IGNORECASE)),
    (
        "access",
        re.compile(
            r"\b(?:year[- ]round|all[- ]weather|direct)\s+(?:road\s+)?access\b", re.IGNORECASE
        ),
    ),
]


def parse_number(value: str, suffix: str | None = None) -> float:
    number = float(value.replace(",", ""))
    return number * ({"m": 1_000_000, "k": 1_000}.get((suffix or "").lower(), 1))


def extract_claims(text: str, source_id: str, source_location: str | None = None) -> list[Claim]:
    claims: list[Claim] = []
    for claim_type, pattern in CLAIM_PATTERNS:
        for match in pattern.finditer(text):
            claims.append(
                Claim(
                    claim_text=match.group(0),
                    claim_type=claim_type,
                    source_id=source_id,
                    source_location=source_location or f"characters {match.start()}-{match.end()}",
                    extraction_confidence=0.85,
                )
            )
    return claims


def extract_buyer_objectives(text: str) -> list[str]:
    objectives: list[str] = []
    patterns = {
        "low flood risk": r"\blow flood risk\b|\bavoid flood",
        "row-crop productivity": r"\brow[- ]crop\b|\bcrop productivity\b",
        "irrigation": r"\bprefer(?:red)? irrigat|\bwant irrigat",
        "low risk": r"\blow[- ]risk\b",
        "long-term investment": r"\blong[- ]term\b",
    }
    for objective, pattern in patterns.items():
        if re.search(pattern, text, re.IGNORECASE):
            objectives.append(objective)
    return objectives


def extract_address_candidate(text: str) -> str | None:
    quoted = re.search(
        r"\b(?:located\s+at|address(?:\s+is)?|at)\b[\s:]+([^.!?\n]+)",
        text,
        re.IGNORECASE,
    )
    if quoted:
        return quoted.group(1).strip()
    location = re.search(
        r"\b(?:in|near)\s+([A-Z][A-Za-z .'-]+,\s*[A-Z]{2}|[A-Z][A-Za-z .'-]+,\s*[A-Z][A-Za-z .'-]+)",
        text,
    )
    return location.group(1).strip() if location else None


class InputResolver:
    def __init__(
        self, geocoder: Geocoder | None = None, listing: ListingAdapter | None = None
    ) -> None:
        self.geocoder = geocoder or Geocoder()
        self.listing = listing or ListingAdapter()

    async def resolve(self, state: InvestigationState) -> InvestigationState:
        text = state.raw_input
        listing_artifact: ListingArtifact | None = None
        source_id = "user_input"
        if state.input_type == InputType.LISTING_URL:
            listing_artifact, listing_evidence = await self.listing.fetch(text)
            state.listing = listing_artifact
            state.evidence.extend(listing_evidence)
            state.limitations.extend(listing_artifact.limitations)
            if listing_artifact.raw_text:
                text = listing_artifact.raw_text
                source_id = str(listing_evidence[0].id) if listing_evidence else "listing"
        else:
            evidence = Evidence(
                source_type=SourceType.USER_PROVIDED,
                source=EvidenceSource(publisher="User", dataset="Investigation input"),
                field_name="input_text",
                value=state.raw_input,
                semantic_scope="user-provided claims and requirements",
                confidence=0.7,
                limitations=["User-provided statements require independent verification."],
            )
            state.evidence.append(evidence)
            source_id = str(evidence.id)

        state.claims.extend(extract_claims(text, source_id))
        state.buyer_objectives = extract_buyer_objectives(text)
        acreage_match = ACRE_PATTERN.search(text)
        acreage = parse_number(acreage_match.group(1)) if acreage_match else None
        price_match = PRICE_PATTERN.search(text)
        asking_price = None
        if price_match:
            value, suffix = (
                (price_match.group(1), price_match.group(2))
                if price_match.group(1)
                else (price_match.group(3), price_match.group(4))
            )
            asking_price = parse_number(value, suffix)
        if state.listing is None:
            state.listing = ListingArtifact(asking_price=asking_price)
        elif asking_price:
            state.listing.asking_price = asking_price

        address = (
            state.raw_input
            if state.input_type == InputType.ADDRESS
            else extract_address_candidate(text)
        )
        if address:
            prop, geocode_evidence, limitations = await self.geocoder.resolve(address)
            state.property = prop
            state.evidence.extend(geocode_evidence)
            state.limitations.extend(limitations)
        if state.property is None:
            state.property = Property(acreage=acreage)
            state.limitations.append(
                "Property location could not be resolved from the supplied input."
            )
        elif acreage:
            state.property.acreage = acreage
        if state.property.latitude is None or state.property.longitude is None:
            state.limitations.append(
                "Coordinates are required before physical and agricultural provider investigations can run."
            )
        return state
