from __future__ import annotations

from dataclasses import dataclass

from app.domain.models import (
    Claim,
    Comparable,
    Contradiction,
    DecisionStability,
    InvestigationState,
    Materiality,
    Unknown,
    Valuation,
    Verdict,
)


def claimed_tillable_acres(claim: Claim) -> float | None:
    import re

    match = re.search(r"([\d,.]+)\s+acres?", claim.claim_text, re.IGNORECASE)
    return float(match.group(1).replace(",", "")) if match else None


class ContradictionEngine:
    def detect(self, state: InvestigationState) -> list[Contradiction]:
        results: list[Contradiction] = []
        tillable_claims = [claim for claim in state.claims if claim.claim_type == "tillable_acres"]
        footprints = [
            item
            for item in state.evidence
            if item.field_name == "cultivated_acres" and isinstance(item.value, (int, float))
        ]
        for claim in tillable_claims:
            claimed = claimed_tillable_acres(claim)
            for evidence in footprints:
                if claimed is None:
                    continue
                if evidence.semantic_scope != "property cultivated footprint":
                    continue
                if not evidence.geometry or evidence.geometry.get("type") not in {
                    "Polygon",
                    "MultiPolygon",
                }:
                    continue
                difference = claimed - float(evidence.value)
                tolerance = max(2.0, claimed * 0.05)
                if abs(difference) <= tolerance:
                    continue
                results.append(
                    Contradiction(
                        claim_id=claim.id,
                        evidence_ids=[evidence.id],
                        description=f"Independent evidence indicates {evidence.value:g} observed cultivated acres versus the {claimed:g}-acre listing claim.",
                        difference_type="potential semantic/spatial discrepancy",
                        resolution_notes=[
                            "Compare compatible geometry, vintage, and definitions before treating this as a contradiction.",
                            "Observed cultivation does not establish legal tillable acreage.",
                        ],
                    )
                )
        return results


class MaterialityEngine:
    def assess(self, state: InvestigationState, contradiction: Contradiction) -> Materiality:
        claim = next(item for item in state.claims if item.id == contradiction.claim_id)
        high_risk = state.buyer_snapshot and state.buyer_snapshot.risk_tolerance.lower() == "low"
        if claim.claim_type == "tillable_acres":
            contradiction.decision_impact = (
                "Potentially changes productive-acre economics and the supported value."
            )
            contradiction.materiality = Materiality.HIGH
        elif claim.claim_type in {"flood", "drainage", "irrigation"}:
            contradiction.materiality = Materiality.HIGH if high_risk else Materiality.MEDIUM
            contradiction.decision_impact = "Could change operational risk and buyer fit."
        else:
            contradiction.materiality = Materiality.LOW
        return contradiction.materiality


class UnknownEngine:
    def identify(self, state: InvestigationState) -> list[Unknown]:
        unknowns: list[Unknown] = [
            item for item in state.unknowns if "resolvable address or coordinate" in item.question
        ]

        def add(question: str, materiality: Materiality, tools: list[str]) -> None:
            if not any(item.question == question for item in unknowns):
                unknowns.append(
                    Unknown(
                        question=question,
                        materiality=materiality,
                        candidate_tools=tools,
                    )
                )

        if not state.property or not state.property.acreage:
            add("What is the authoritative total acreage?", Materiality.HIGH, [])
        if not any(item.field_name == "value_per_acre" for item in state.evidence):
            add(
                "What regional market benchmark is supportable?",
                Materiality.HIGH,
                ["market.get_benchmark"],
            )
        field_names = {item.field_name for item in state.evidence}
        has_production = bool(
            field_names
            & {"yield_per_acre", "expected_yield", "production_per_unit", "milk_yield_per_head"}
        )
        has_price = bool(field_names & {"commodity_price", "price_per_unit"})
        has_cost = bool(
            field_names
            & {"operating_cost_per_acre", "operating_cost_per_unit", "operating_cost_per_head"}
        )
        economics_is_material = bool(state.user_objective.agricultural_activities) or (
            state.user_objective.objective.value
            in {"maximize_profit", "crop", "dairy", "livestock", "grazing", "investment"}
        )
        if economics_is_material and not (has_production and has_price and has_cost):
            add(
                "What sourced production, price, and operating-cost assumptions support the proposed agricultural use?",
                Materiality.HIGH,
                ["agriculture.get_economics"],
            )
        if not any(item.field_name == "comparable_value_per_acre" for item in state.evidence):
            add(
                "Are there traceable comparable agricultural transactions?",
                Materiality.MEDIUM,
                ["market.find_comparables"],
            )
        unresolved_claims = [
            claim
            for claim in state.claims
            if claim.state
            not in {
                "SUPPORTED",
                "PARTIALLY_SUPPORTED",
                "CONTRADICTED",
                "NOT_MATERIAL",
            }
        ]
        for claim in unresolved_claims:
            if claim.claim_type == "tillable_acres":
                add(
                    "Does reliable property-scope evidence corroborate the claimed tillable acreage?",
                    Materiality.HIGH,
                    ["agriculture.get_crop_history"],
                )
            elif claim.claim_type in {"drainage", "soil_quality"}:
                add(
                    f"What independent soil/drainage evidence addresses '{claim.claim_text}'?",
                    Materiality.MEDIUM,
                    ["agriculture.get_soil_context"],
                )
            elif claim.claim_type in {"irrigation", "flood", "access"}:
                add(
                    f"What independent physical evidence addresses '{claim.claim_text}'?",
                    claim.materiality or Materiality.MEDIUM,
                    ["mireye.fetch_context"],
                )
        return unknowns


@dataclass(frozen=True)
class InvestigationCandidate:
    name: str
    expected_decision_improvement: float
    materiality: float
    uncertainty: float
    reliability: float
    cost: float
    rationale: str

    @property
    def value(self) -> float:
        return (
            self.expected_decision_improvement
            * self.materiality
            * self.uncertainty
            * self.reliability
            - self.cost
        )


class ValueOfInformationEngine:
    def rank(self, candidates: list[InvestigationCandidate]) -> list[InvestigationCandidate]:
        return sorted(candidates, key=lambda item: (-item.value, item.name))


class DecisionStabilityEngine:
    def evaluate(self, state: InvestigationState) -> DecisionStability:
        valuation = state.valuation
        high_risk = any(
            item.materiality == Materiality.HIGH for item in state.contradictions
        ) or any(item.materiality == Materiality.HIGH for item in state.unknowns)
        if (
            not valuation
            or valuation.low is None
            or valuation.high is None
            or valuation.asking_price is None
        ):
            return DecisionStability(
                stable=False,
                classification="UNBOUNDED",
                explanation="The verdict cannot be stress-tested because asking price or valuation bounds are unavailable.",
                downside_verdict=Verdict.DO_NOT_ACQUIRE,
                upside_verdict=Verdict.DO_NOT_ACQUIRE,
            )
        downside = (
            Verdict.ACQUIRE
            if valuation.asking_price <= valuation.low and not high_risk
            else Verdict.DO_NOT_ACQUIRE
        )
        upside = (
            Verdict.ACQUIRE
            if valuation.asking_price <= valuation.high and not high_risk
            else Verdict.DO_NOT_ACQUIRE
        )
        stable = downside == upside
        return DecisionStability(
            stable=stable,
            classification=(
                "STABLE_ACQUIRE"
                if stable and upside == Verdict.ACQUIRE
                else "STABLE_DO_NOT_ACQUIRE"
                if stable
                else "PRICE_SENSITIVE"
            ),
            explanation=(
                "The verdict is unchanged across the current valuation range."
                if stable
                else "The verdict changes between the low and high valuation bounds; more evidence or price protection is material."
            ),
            downside_verdict=downside,
            upside_verdict=upside,
        )


class ValuationEngine:
    def calculate(self, state: InvestigationState) -> Valuation:
        benchmarks = [
            item
            for item in state.evidence
            if item.field_name in {"value_per_acre", "comparable_value_per_acre"}
            and isinstance(item.value, (int, float))
        ]
        asking = state.listing.asking_price if state.listing else None
        acres = state.property.acreage if state.property else None
        if not benchmarks or not acres:
            missing = []
            if not benchmarks:
                missing.append("No traceable market benchmark is available.")
            if not acres:
                missing.append("Total acreage is unresolved.")
            return Valuation(asking_price=asking, confidence=0, limitations=missing)
        weights = [max(item.confidence, 0.1) for item in benchmarks]
        per_acre = sum(
            float(item.value) * weight for item, weight in zip(benchmarks, weights)
        ) / sum(weights)
        comparable_evidence = [
            item for item in benchmarks if item.field_name == "comparable_value_per_acre"
        ]
        state.comparables = []
        for item in comparable_evidence:
            raw = item.raw_reference.get("comparable", {})
            if not isinstance(raw, dict):
                continue
            try:
                state.comparables.append(
                    Comparable(
                        source_url=raw.get("source_url") or item.source.url,
                        location=raw.get("location"),
                        sale_price=float(raw["sale_price"]),
                        acreage=float(raw["acreage"]),
                        price_per_acre=float(item.value),
                        sale_date=raw.get("sale_date"),
                        adjustments=raw.get("adjustments", []),
                        evidence_id=item.id,
                    )
                )
            except (KeyError, TypeError, ValueError):
                continue
        spread = 0.2
        if len(benchmarks) >= 3:
            spread -= 0.05
        if state.contradictions:
            spread += 0.1
        if any(item.materiality == Materiality.HIGH for item in state.unknowns):
            spread += 0.1
        spread = min(0.45, max(0.1, spread))
        total = per_acre * acres
        low, high = total * (1 - spread), total * (1 + spread)
        return Valuation(
            estimated_value_total=round(total, 2),
            estimated_value_per_acre=round(per_acre, 2),
            low=round(low, 2),
            high=round(high, 2),
            asking_price=asking,
            price_gap=round(asking - total, 2) if asking else None,
            confidence=min(0.85, sum(weights) / len(weights)),
            key_value_drivers=[
                f"Weighted indication from {len(benchmarks)} traceable market observation(s): approximately ${per_acre:,.0f} per acre"
            ],
            key_downside_drivers=[
                item.description
                for item in state.contradictions
                if item.materiality == Materiality.HIGH
            ],
            assumptions=["Regional benchmark is applicable only as a starting indication."],
            evidence_ids=[item.id for item in benchmarks],
            limitations=[
                "No unsupported property-specific adjustment was applied; field and comparable verification remain necessary.",
                f"The {spread:.0%} range reflects evidence count, unresolved unknowns, and contradiction risk rather than statistical certainty.",
            ],
        )
