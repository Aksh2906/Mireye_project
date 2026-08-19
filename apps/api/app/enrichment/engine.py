from __future__ import annotations

from collections import Counter
from itertools import pairwise
from typing import Any

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
        signals.extend(self._physical_consistency(state))
        signals.extend(self._operational_context(state))
        return signals

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
            bool(item.value["is_agricultural"])
            for item in crop
            if isinstance(item.value, dict) and "is_agricultural" in item.value
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
