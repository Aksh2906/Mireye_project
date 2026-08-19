from app.domain.models import (
    ClaimState,
    ClaimStateTransition,
    ClaimTransitionProposal,
    InvestigationState,
)

ALLOWED_TRANSITIONS: dict[ClaimState, set[ClaimState]] = {
    ClaimState.UNKNOWN: {
        ClaimState.LOW_CONFIDENCE,
        ClaimState.UNDER_INVESTIGATION,
        ClaimState.NOT_MATERIAL,
    },
    ClaimState.LOW_CONFIDENCE: {
        ClaimState.UNDER_INVESTIGATION,
        ClaimState.SUPPORTED,
        ClaimState.PARTIALLY_SUPPORTED,
        ClaimState.CONTRADICTED,
        ClaimState.NOT_MATERIAL,
    },
    ClaimState.UNDER_INVESTIGATION: {
        ClaimState.SUPPORTED,
        ClaimState.PARTIALLY_SUPPORTED,
        ClaimState.CONTRADICTED,
        ClaimState.NOT_MATERIAL,
    },
    ClaimState.SUPPORTED: {ClaimState.PARTIALLY_SUPPORTED, ClaimState.CONTRADICTED},
    ClaimState.PARTIALLY_SUPPORTED: {
        ClaimState.SUPPORTED,
        ClaimState.CONTRADICTED,
        ClaimState.NOT_MATERIAL,
    },
    ClaimState.CONTRADICTED: {
        ClaimState.PARTIALLY_SUPPORTED,
        ClaimState.SUPPORTED,
        ClaimState.NOT_MATERIAL,
    },
    ClaimState.NOT_MATERIAL: set(),
}


def apply_claim_transition(state: InvestigationState, proposal: ClaimTransitionProposal) -> None:
    claim = next((item for item in state.claims if item.id == proposal.claim_id), None)
    if claim is None:
        raise ValueError("Referenced claim does not exist")
    evidence_ids = {item.id for item in state.evidence}
    if not proposal.evidence_ids or not set(proposal.evidence_ids).issubset(evidence_ids):
        raise ValueError("Transition must reference existing evidence")
    if proposal.target_state not in ALLOWED_TRANSITIONS[claim.state]:
        raise ValueError(f"Transition {claim.state} -> {proposal.target_state} is not permitted")
    if (
        proposal.target_state in {ClaimState.SUPPORTED, ClaimState.CONTRADICTED}
        and proposal.confidence < 0.6
    ):
        raise ValueError("Conclusive transitions require confidence >= 0.6")
    previous = claim.state
    claim.state = proposal.target_state
    state.claim_transitions.append(
        ClaimStateTransition(
            claim_id=claim.id,
            from_state=previous,
            to_state=proposal.target_state,
            evidence_ids=proposal.evidence_ids,
            confidence=proposal.confidence,
            rationale=proposal.rationale,
        )
    )
