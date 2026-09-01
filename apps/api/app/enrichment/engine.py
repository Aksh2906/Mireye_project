from __future__ import annotations

from collections import Counter
from itertools import pairwise
from typing import Any

from app.connectors.agriculture import is_agricultural_category
from app.domain.models import (
    DerivedSignal,
    InvestigationState,
    Materiality,
    SourceType,
)
from app.investigation.engines import claimed_tillable_acres


def _crop_category(value: Any) -> str | None:
    if isinstance(value, dict) and value.get("category"):
        return str(value["category"])
    return str(value) if isinstance(value, str) and value else None


class EnrichmentEngine:
    def derive(self, state: InvestigationState) -> list[DerivedSignal]:
        signals: list[DerivedSignal] = []
        signals.extend(self._crop_signals(state))
        signals.extend(self._seller_divergence(state))
        signals.extend(self._boundary_divergence(state))
        signals.extend(self._physical_consistency(state))
        signals.extend(self._operational_context(state))
        signals.extend(self._activity_fit(state))
        signals.extend(self._infrastructure_burden(state))
        signals.extend(self._hazard_exposure(state))
        signals.extend(self._premium_justification(state))
        signals.extend(self._alternative_delta(state))
        return signals

    def _boundary_divergence(self, state: InvestigationState) -> list[DerivedSignal]:
        claimed = state.property.acreage if state.property else None
        areas = [
            item
            for item in state.evidence
            if item.field_name == "boundary_area_acres" and isinstance(item.value, (int, float))
        ]
        if not claimed or not areas:
            return []
        area = max(areas, key=lambda item: item.confidence)
        difference = float(area.value) - claimed
        ratio = abs(difference) / claimed
        return [
            DerivedSignal(
                name="Boundary area divergence",
                value=round(difference, 2),
                interpretation=f"The available boundary-derived area differs from claimed acreage by {difference:+.2f} acres.",
                materiality=Materiality.HIGH
                if ratio >= 0.1
                else Materiality.MEDIUM
                if ratio >= 0.05
                else Materiality.LOW,
                evidence_ids=[area.id],
                method="Calculate geodesic polygon area and subtract claimed acreage.",
                confidence=area.confidence,
                applicable_objectives=["crop", "grazing", "investment", "maximize_profit"],
                limitations=["Analysis geometry is not a survey or legal parcel determination."],
            )
        ]

    def _crop_signals(self, state: InvestigationState) -> list[DerivedSignal]:
        crop = [
            item
            for item in state.evidence
            if item.source_type == SourceType.USDA_CDL and item.value is not None
        ]
        if not crop:
            return []
        signals: list[DerivedSignal] = []
        classified = [
            is_agricultural_category(str(item.value["category"]))
            for item in crop
            if isinstance(item.value, dict) and item.value.get("category")
        ]
        if classified:
            continuity = sum(classified) / len(classified)
            signals.append(
                DerivedSignal(
                    name="Agricultural continuity",
                    value=continuity,
                    interpretation=(
                        f"Agricultural classes were observed in {sum(classified)} of "
                        f"{len(classified)} valid annual CDL point observations."
                    ),
                    materiality=Materiality.MEDIUM,
                    evidence_ids=[item.id for item in crop],
                    method=(
                        "Count annual CDL observations classified as agricultural and divide "
                        "by valid annual observations."
                    ),
                    limitations=[
                        "CDL is a classified raster proxy, not proof of productivity or tillable acreage.",
                        "Point observations do not represent a whole property without reliable geometry.",
                    ],
                )
            )
        categories = [category for item in crop if (category := _crop_category(item.value))]
        if len(categories) >= 2:
            transitions = sum(left != right for left, right in pairwise(categories))
            signals.append(
                DerivedSignal(
                    name="Land use drift",
                    value=transitions,
                    interpretation=(
                        f"The observed CDL class changed {transitions} time(s) across "
                        f"{len(categories)} ordered annual observations."
                    ),
                    materiality=Materiality.MEDIUM if transitions else Materiality.LOW,
                    evidence_ids=[item.id for item in crop],
                    method="Count changes between consecutive annual CDL class observations.",
                    limitations=[
                        "Crop rotations can produce class changes without indicating degradation.",
                        "Dataset classification error and point sampling can create apparent changes.",
                    ],
                )
            )
            dominant, count = Counter(categories).most_common(1)[0]
            signals.append(
                DerivedSignal(
                    name="Observed class consistency",
                    value=count / len(categories),
                    interpretation=(
                        f"The most frequent observed class ({dominant}) occurred in {count} of "
                        f"{len(categories)} annual observations."
                    ),
                    materiality=Materiality.LOW,
                    evidence_ids=[item.id for item in crop],
                    method="Frequency of the modal CDL class divided by valid annual observations.",
                    limitations=["Class consistency is not a yield or profitability measure."],
                )
            )
        return signals

    def _seller_divergence(self, state: InvestigationState) -> list[DerivedSignal]:
        signals: list[DerivedSignal] = []
        footprints = [
            item
            for item in state.evidence
            if item.field_name == "cultivated_acres"
            and isinstance(item.value, (int, float))
            and item.semantic_scope == "property cultivated footprint"
            and item.geometry
            and item.geometry.get("type") in {"Polygon", "MultiPolygon"}
        ]
        for claim in (item for item in state.claims if item.claim_type == "tillable_acres"):
            claimed = claimed_tillable_acres(claim)
            if claimed is None:
                continue
            for evidence in footprints:
                divergence = claimed - float(evidence.value)
                ratio = abs(divergence) / claimed if claimed else 0
                materiality = Materiality.HIGH if ratio >= 0.1 else Materiality.MEDIUM
                signals.append(
                    DerivedSignal(
                        name="Seller claim divergence",
                        value=divergence,
                        interpretation=(
                            f"Independent property-scope evidence differs from the seller's "
                            f"tillable-acre claim by {divergence:g} acres. This does not prove "
                            "the seller's definition is false."
                        ),
                        materiality=materiality,
                        evidence_ids=[evidence.id],
                        method="Subtract independent observed cultivated acres from claimed tillable acres.",
                        limitations=[
                            "Observed cultivation and legal/tillable acreage are not identical concepts.",
                            "Geometry, vintage, and measurement method must be verified.",
                        ],
                    )
                )
        return signals

    def _physical_consistency(self, state: InvestigationState) -> list[DerivedSignal]:
        relevant = [
            item
            for item in state.evidence
            if item.source_type in {SourceType.MIREYE, SourceType.USDA_CDL, SourceType.USDA_SSURGO}
        ]
        source_types = {item.source_type for item in relevant}
        if len(source_types) < 2:
            return []
        return [
            DerivedSignal(
                name="Physical-agricultural consistency",
                value="REVIEWABLE",
                interpretation=(
                    "Independent physical, crop, and/or soil evidence is available for cross-source "
                    "consistency review; absence of a detected contradiction is not proof of consistency."
                ),
                materiality=Materiality.MEDIUM,
                evidence_ids=[item.id for item in relevant],
                method="Group independent physical and agricultural evidence by source type for comparison.",
                limitations=[
                    "A conclusive consistency result requires compatible geometry, semantics, and vintage."
                ],
            )
        ]

    def _operational_context(self, state: InvestigationState) -> list[DerivedSignal]:
        signals: list[DerivedSignal] = []
        field_groups = {
            "Access/operational friction": ("access", "road", "slope", "terrain"),
            "Water/drainage risk signal": ("water", "drain", "flood", "wetness", "hydro"),
        }
        for signal_name, keywords in field_groups.items():
            evidence = [
                item
                for item in state.evidence
                if any(keyword in item.field_name.casefold() for keyword in keywords)
                and item.source_type in {SourceType.MIREYE, SourceType.USDA_SSURGO}
            ]
            if not evidence:
                continue
            signals.append(
                DerivedSignal(
                    name=signal_name,
                    value="EVIDENCE_PRESENT",
                    interpretation=(
                        f"{len(evidence)} independently sourced field(s) are relevant to "
                        f"{signal_name.casefold()} and require buyer-specific interpretation."
                    ),
                    materiality=Materiality.MEDIUM,
                    evidence_ids=[item.id for item in evidence],
                    method=(
                        "Select provenance-preserved provider fields whose documented names are directly "
                        f"relevant to {', '.join(keywords)}; no undocumented threshold is applied."
                    ),
                    limitations=[
                        "This signal identifies relevant evidence; it does not establish legal access or water rights."
                    ],
                )
            )
        return signals

    def _activity_fit(self, state: InvestigationState) -> list[DerivedSignal]:
        crop = [item for item in state.evidence if item.source_type == SourceType.USDA_CDL]
        physical = [
            item
            for item in state.evidence
            if item.source_type in {SourceType.MIREYE, SourceType.USDA_SSURGO}
        ]
        if not crop or not physical:
            return []
        agricultural = [
            item
            for item in crop
            if isinstance(item.value, dict)
            and item.value.get("category")
            and is_agricultural_category(str(item.value["category"]))
        ]
        categories = [
            str(item.value.get("category", "")).casefold()
            for item in crop
            if isinstance(item.value, dict)
        ]
        pasture = sum(
            any(word in value for word in ("pasture", "grass", "hay")) for value in categories
        )
        common_limitations = [
            "Compatibility is not a profitability finding.",
            "Property-wide applicability depends on reliable parcel geometry and compatible resolution.",
        ]
        signals = [
            DerivedSignal(
                name="Agricultural intensity potential",
                value="MODERATE" if agricultural else "WEAK",
                interpretation=f"Historical agricultural classification and {len(physical)} physical-context observation(s) provide a multi-source basis for activity screening.",
                materiality=Materiality.HIGH,
                evidence_ids=[item.id for item in agricultural + physical],
                method="Combine historical agricultural classifications with independently sourced physical context; no opaque master score is used.",
                confidence=min(
                    0.75,
                    sum(item.confidence for item in agricultural + physical)
                    / max(1, len(agricultural + physical)),
                ),
                applicable_objectives=["crop", "grazing", "livestock", "maximize_profit"],
                limitations=common_limitations,
            )
        ]
        if agricultural:
            signals.append(
                DerivedSignal(
                    name="Crop fit",
                    value="SUPPORTED_FOR_DEEPER_REVIEW",
                    interpretation="Repeated agricultural land-cover evidence plus physical context supports deeper crop-specific investigation.",
                    materiality=Materiality.HIGH,
                    evidence_ids=[item.id for item in agricultural + physical],
                    method="Require agricultural history and independent physical context before advancing crop candidates.",
                    confidence=min(0.8, len(agricultural) / max(1, len(crop))),
                    applicable_objectives=["crop", "maximize_profit"],
                    limitations=common_limitations,
                )
            )
        if pasture:
            signals.append(
                DerivedSignal(
                    name="Grazing opportunity",
                    value="SUPPORTED_FOR_DEEPER_REVIEW",
                    interpretation=f"Pasture, grass, or hay appears in {pasture} historical observation(s), with independent physical context available.",
                    materiality=Materiality.HIGH,
                    evidence_ids=[item.id for item in crop + physical],
                    method="Combine pasture-like historical classes with physical context; stocking rate and water sufficiency remain unproven.",
                    confidence=min(0.8, pasture / max(1, len(crop))),
                    applicable_objectives=["grazing", "livestock"],
                    limitations=common_limitations + ["This does not establish carrying capacity."],
                )
            )
        return signals

    def _infrastructure_burden(self, state: InvestigationState) -> list[DerivedSignal]:
        relevant = [
            item
            for item in state.evidence
            if any(
                word in item.field_name.casefold()
                for word in ("water", "irrig", "road", "access", "utility", "fence")
            )
        ]
        claims = [item for item in state.claims if item.claim_type in {"irrigation", "access"}]
        if not relevant and not claims:
            return []
        unresolved = [
            item for item in claims if item.state not in {"SUPPORTED", "PARTIALLY_SUPPORTED"}
        ]
        return [
            DerivedSignal(
                name="Infrastructure burden",
                value="UNCERTAIN" if unresolved else "EVIDENCE_PRESENT",
                interpretation=f"{len(relevant)} context observation(s) and {len(unresolved)} unresolved infrastructure claim(s) affect readiness for the intended use.",
                materiality=Materiality.HIGH if unresolved else Materiality.MEDIUM,
                evidence_ids=[item.id for item in relevant],
                method="Relate water, irrigation, access, utility, and fencing evidence to unresolved listing claims.",
                confidence=max((item.confidence for item in relevant), default=0.3),
                applicable_objectives=["crop", "grazing", "livestock", "dairy"],
                limitations=[
                    "Nearby infrastructure does not establish capacity, condition, permits, or legal rights."
                ],
            )
        ]

    def _hazard_exposure(self, state: InvestigationState) -> list[DerivedSignal]:
        evidence = [
            item
            for item in state.evidence
            if any(
                word in item.field_name.casefold()
                for word in (
                    "flood",
                    "fire",
                    "drought",
                    "heat",
                    "storm",
                    "hail",
                    "erosion",
                    "landslide",
                )
            )
        ]
        if not evidence:
            return []
        return [
            DerivedSignal(
                name="Hazard-adjusted agricultural exposure",
                value="REQUIRES_ACTIVITY_REVIEW",
                interpretation=f"{len(evidence)} hazard-context observation(s) may have different consequences for the buyer's candidate agricultural activities.",
                materiality=Materiality.HIGH,
                evidence_ids=[item.id for item in evidence],
                method="Identify hazard evidence, then defer materiality to activity-specific consequence analysis and buyer risk tolerance.",
                confidence=sum(item.confidence for item in evidence) / len(evidence),
                applicable_objectives=["crop", "grazing", "livestock", "minimize_risk"],
                limitations=[
                    "A missing hazard observation is not evidence that the hazard is absent."
                ],
            )
        ]

    def _premium_justification(self, state: InvestigationState) -> list[DerivedSignal]:
        if not state.alternatives or not state.listing or state.listing.asking_price is None:
            return []
        reviewed = [item for item in state.alternatives if item.price is not None]
        if not reviewed:
            return []
        return [
            DerivedSignal(
                name="Premium-pricing justification",
                value="COMPARISON_REQUIRED",
                interpretation=f"{len(reviewed)} priced alternative(s) are available; any premium must be explained through usable area, required investment, risk, and sourced scenario economics.",
                materiality=Materiality.HIGH,
                evidence_ids=[],
                method="Compare incremental acquisition price with evidence-backed incremental agricultural benefit; do not use an opaque weighted score.",
                confidence=0.4,
                applicable_objectives=["maximize_profit", "investment"],
                limitations=[
                    "A premium cannot be justified without comparable activity economics and equivalent evidence depth."
                ],
            )
        ]

    def _alternative_delta(self, state: InvestigationState) -> list[DerivedSignal]:
        signals: list[DerivedSignal] = []
        for alternative in state.alternatives:
            if not (alternative.advantages or alternative.disadvantages):
                continue
            signals.append(
                DerivedSignal(
                    name="Alternative opportunity delta",
                    value=str(alternative.id),
                    interpretation=(
                        f"The screened alternative has {len(alternative.advantages)} stated advantage(s), "
                        f"{len(alternative.disadvantages)} disadvantage(s), and {len(alternative.unknowns)} material unknown(s) relative to the buyer objective."
                    ),
                    materiality=Materiality.HIGH,
                    evidence_ids=[],
                    method="Explain objective-specific advantages, disadvantages, and unknowns without converting them to a master score.",
                    confidence=alternative.evidence_quality,
                    applicable_objectives=["maximize_profit", "investment", "balanced"],
                    limitations=[
                        "Screened listing attributes are claims until independently investigated at equivalent depth."
                    ],
                )
            )
        return signals
