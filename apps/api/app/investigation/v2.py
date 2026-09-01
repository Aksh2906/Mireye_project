from __future__ import annotations

from typing import ClassVar

from app.domain.models import (
    Hypothesis,
    HypothesisStatus,
    InvestigationAction,
    InvestigationState,
    Materiality,
)


class HypothesisEngine:
    def initialize(self, state: InvestigationState) -> None:
        if state.hypotheses:
            return
        state.hypotheses = [
            Hypothesis(
                statement="The property can support the buyer's intended agricultural use.",
                importance="high",
                materiality=0.9,
            ),
            Hypothesis(
                statement="The listing's material acreage and infrastructure claims are supportable.",
                importance="high",
                materiality=0.9,
            ),
            Hypothesis(
                statement="The acquisition price is economically defensible under sourced assumptions.",
                importance="high",
                materiality=1.0,
            ),
            Hypothesis(
                statement="Material hazards remain acceptable for the intended activity and risk tolerance.",
                importance="high",
                materiality=0.85,
            ),
        ]
        if state.user_objective.willingness_to_pay_premium:
            state.hypotheses.append(
                Hypothesis(
                    statement="Superior agricultural economics may justify a price premium.",
                    importance="medium",
                    materiality=0.75,
                )
            )

    def update(self, state: InvestigationState) -> None:
        for index, hypothesis in enumerate(state.hypotheses):
            if index == 0:
                signals = [
                    item
                    for item in state.signals
                    if item.name in {"Agricultural continuity", "Crop fit", "Grazing opportunity"}
                ]
                hypothesis.supporting_evidence_ids = [
                    eid for item in signals for eid in item.evidence_ids
                ]
                if hypothesis.supporting_evidence_ids:
                    hypothesis.status = HypothesisStatus.PARTIALLY_SUPPORTED
                    hypothesis.confidence = max(item.confidence for item in signals)
            elif index == 1 and state.contradictions:
                hypothesis.status = HypothesisStatus.CONTRADICTED
                hypothesis.conflicting_evidence_ids = [
                    eid for item in state.contradictions for eid in item.evidence_ids
                ]
                hypothesis.confidence = max(
                    0.6,
                    max(
                        (item.materiality == Materiality.HIGH) * 0.8
                        for item in state.contradictions
                    ),
                )
            elif index == 2 and state.economic_scenarios:
                base = next(
                    (item for item in state.economic_scenarios if item.name == "base"), None
                )
                hypothesis.status = (
                    HypothesisStatus.PARTIALLY_SUPPORTED
                    if base and (base.annual_operating_profit or 0) > 0
                    else HypothesisStatus.CONTRADICTED
                )
                hypothesis.confidence = base.confidence if base else 0
            elif index == 3 and state.hazard_assessments:
                high = any(
                    item.materiality == Materiality.HIGH for item in state.hazard_assessments
                )
                hypothesis.status = (
                    HypothesisStatus.CONTRADICTED if high else HypothesisStatus.PARTIALLY_SUPPORTED
                )
                hypothesis.confidence = max(item.confidence for item in state.hazard_assessments)


class ActionRegistry:
    ACTION_TYPES: ClassVar[dict[str, str]] = {
        "mireye.fetch_context": "fetch_mireye",
        "agriculture.get_crop_history": "fetch_crop_history",
        "agriculture.get_soil_context": "fetch_soil",
        "agriculture.get_economics": "fetch_ag_economics",
        "hazard.get_context": "fetch_hazard",
        "listing.search": "search_listings",
        "market.get_benchmark": "fetch_ag_economics",
        "market.find_comparables": "fetch_ag_economics",
    }

    def build(self, candidates) -> list[InvestigationAction]:
        actions = []
        for candidate in candidates:
            actions.append(
                InvestigationAction(
                    type=self.ACTION_TYPES.get(candidate.name, candidate.name),
                    target=candidate.name,
                    expected_information_gain=candidate.uncertainty * candidate.reliability,
                    expected_decision_impact=candidate.expected_decision_improvement
                    * candidate.materiality,
                    estimated_cost=candidate.cost,
                    reason=candidate.rationale,
                    voi=candidate.value,
                )
            )
        return actions
