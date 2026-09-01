from __future__ import annotations

from app.domain.models import InvestigationState


def calculate_behavior_metrics(state: InvestigationState) -> dict[str, float | int | bool]:
    relevant_ids = {evidence_id for signal in state.signals for evidence_id in signal.evidence_ids}
    relevant_ids.update(
        evidence_id
        for contradiction in state.contradictions
        for evidence_id in contradiction.evidence_ids
    )
    if state.valuation:
        relevant_ids.update(state.valuation.evidence_ids)
    relevant_count = sum(item.id in relevant_ids for item in state.evidence)
    total = len(state.evidence)
    unavailable_calls = sum(item.status == "unavailable" for item in state.tool_calls)
    return {
        "tool_calls": len(state.tool_calls),
        "unavailable_tool_calls": unavailable_calls,
        "material_contradictions_detected": sum(
            item.materiality.value == "HIGH" for item in state.contradictions
        ),
        "decision_relevant_evidence_ratio": relevant_count / total if total else 0.0,
        "alternative_search_triggered": any(
            item.tool_name == "listing.search" for item in state.tool_calls
        ),
        "terminated_with_reason": bool(state.termination_reason),
        "recommendation_evidence_coverage": bool(
            (state.valuation and state.valuation.evidence_ids) or state.signals
        ),
    }
