from app.domain.models import InvestigationState


def generate_dossier(state: InvestigationState) -> dict:
    """Render only validated world-model facts; never introduces new facts."""
    return {
        "property": state.property.model_dump(mode="json") if state.property else None,
        "verdict": state.decision.model_dump(mode="json") if state.decision else None,
        "executive_thesis": state.decision.decision_summary
        if state.decision
        else "Investigation incomplete.",
        "seller_claims": [item.model_dump(mode="json") for item in state.claims],
        "claim_transition_history": [
            item.model_dump(mode="json") for item in state.claim_transitions
        ],
        "agricultural_analysis": [item.model_dump(mode="json") for item in state.signals],
        "buyer_objective": state.user_objective.model_dump(mode="json"),
        "boundary": state.boundary.model_dump(mode="json") if state.boundary else None,
        "hypotheses": [item.model_dump(mode="json") for item in state.hypotheses],
        "crop_opportunities": [item.model_dump(mode="json") for item in state.crop_opportunities],
        "activity_opportunities": [
            item.model_dump(mode="json") for item in state.activity_opportunities
        ],
        "economic_scenarios": [item.model_dump(mode="json") for item in state.economic_scenarios],
        "financial_inputs": state.financial_inputs.model_dump(mode="json"),
        "investment_decision": state.investment_decision.model_dump(mode="json")
        if state.investment_decision
        else None,
        "hazard_assessments": [item.model_dump(mode="json") for item in state.hazard_assessments],
        "alternatives": [item.model_dump(mode="json") for item in state.alternatives],
        "searched_radii_miles": state.searched_radii_miles,
        "contradictions": [item.model_dump(mode="json") for item in state.contradictions],
        "valuation": state.valuation.model_dump(mode="json") if state.valuation else None,
        "comparables": [item.model_dump(mode="json") for item in state.comparables],
        "decision_stability": state.decision_stability.model_dump(mode="json")
        if state.decision_stability
        else None,
        "risks": [
            item.description
            for item in state.contradictions
            if item.materiality in {"MEDIUM", "HIGH"}
        ],
        "unknowns": [item.model_dump(mode="json") for item in state.unknowns],
        "due_diligence": [item.model_dump(mode="json") for item in state.diligence],
        "negotiation_strategy": [item.model_dump(mode="json") for item in state.negotiation],
        "evidence": [item.model_dump(mode="json") for item in state.evidence],
        "trace": {
            "events": [item.model_dump(mode="json") for item in state.events],
            "agent_runs": [item.model_dump(mode="json") for item in state.agent_runs],
            "tool_calls": [item.model_dump(mode="json") for item in state.tool_calls],
            "candidate_actions": [item.model_dump(mode="json") for item in state.candidate_actions],
            "executed_actions": [item.model_dump(mode="json") for item in state.executed_actions],
            "iteration": state.iteration,
            "termination_reason": state.termination_reason,
        },
        "limitations": state.limitations,
    }
