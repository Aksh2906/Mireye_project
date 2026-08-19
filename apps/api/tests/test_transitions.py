import unittest

from app.domain.models import (
    Claim,
    ClaimState,
    ClaimTransitionProposal,
    Evidence,
    EvidenceSource,
    InputType,
    InvestigationState,
    SourceType,
)
from app.world_model.transitions import apply_claim_transition


class TransitionTests(unittest.TestCase):
    def test_transition_requires_existing_evidence(self):
        item = InvestigationState(input_type=InputType.QUERY, raw_input="farm")
        claim = Claim(
            claim_text="irrigated",
            claim_type="irrigation",
            source_id="listing",
            extraction_confidence=0.9,
        )
        item.claims.append(claim)
        with self.assertRaises(ValueError):
            apply_claim_transition(
                item,
                ClaimTransitionProposal(
                    claim_id=claim.id,
                    target_state=ClaimState.UNDER_INVESTIGATION,
                    evidence_ids=[],
                    confidence=0.8,
                    rationale="test",
                ),
            )

    def test_validated_transition(self):
        item = InvestigationState(input_type=InputType.QUERY, raw_input="farm")
        claim = Claim(
            claim_text="irrigated",
            claim_type="irrigation",
            source_id="listing",
            extraction_confidence=0.9,
        )
        evidence = Evidence(
            source_type=SourceType.MIREYE,
            source=EvidenceSource(publisher="Mireye", dataset="context"),
            field_name="water_context",
            value="observed",
        )
        item.claims.append(claim)
        item.evidence.append(evidence)
        apply_claim_transition(
            item,
            ClaimTransitionProposal(
                claim_id=claim.id,
                target_state=ClaimState.UNDER_INVESTIGATION,
                evidence_ids=[evidence.id],
                confidence=0.8,
                rationale="investigate",
            ),
        )
        self.assertEqual(claim.state, ClaimState.UNDER_INVESTIGATION)
        self.assertEqual(len(item.claim_transitions), 1)
        self.assertEqual(item.claim_transitions[0].from_state, ClaimState.UNKNOWN)
