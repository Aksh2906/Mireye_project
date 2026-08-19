import unittest

from app.domain.models import (
    Claim,
    Evidence,
    EvidenceSource,
    InputType,
    InvestigationState,
    ListingArtifact,
    Materiality,
    Property,
    SourceType,
)
from app.investigation.engines import (
    ContradictionEngine,
    InvestigationCandidate,
    MaterialityEngine,
    ValuationEngine,
    ValueOfInformationEngine,
)


def state() -> InvestigationState:
    return InvestigationState(
        input_type=InputType.QUERY,
        raw_input="farm",
        property=Property(acreage=100),
        listing=ListingArtifact(asking_price=700_000),
    )


class EngineTests(unittest.TestCase):
    def test_voi_is_deterministic(self):
        low = InvestigationCandidate("low", 0.2, 0.2, 0.2, 0.5, 0.1, "")
        high = InvestigationCandidate("high", 0.9, 0.9, 0.9, 0.8, 0.1, "")
        self.assertEqual(ValueOfInformationEngine().rank([low, high])[0].name, "high")

    def test_valuation_is_a_range(self):
        item = state()
        evidence = Evidence(
            source_type=SourceType.MARKET_DATA,
            source=EvidenceSource(publisher="USDA", dataset="benchmark"),
            field_name="value_per_acre",
            value=7000,
            confidence=0.8,
        )
        item.evidence.append(evidence)
        valuation = ValuationEngine().calculate(item)
        self.assertLess(valuation.low, valuation.estimated_value_total)
        self.assertGreater(valuation.high, valuation.estimated_value_total)
        self.assertEqual(valuation.evidence_ids, [evidence.id])

    def test_missing_market_data_does_not_fabricate_value(self):
        valuation = ValuationEngine().calculate(state())
        self.assertIsNone(valuation.estimated_value_total)
        self.assertTrue(valuation.limitations)

    def test_resolution_mismatch_is_not_a_contradiction(self):
        item = state()
        item.claims.append(
            Claim(
                claim_text="70 acres tillable",
                claim_type="tillable_acres",
                source_id="listing",
                extraction_confidence=0.9,
            )
        )
        item.evidence.append(
            Evidence(
                source_type=SourceType.USDA_CDL,
                source=EvidenceSource(publisher="USDA", dataset="CDL"),
                field_name="cultivated_acres",
                value=60,
                semantic_scope="point raster proxy",
                geometry={"type": "Point", "coordinates": [0, 0]},
            )
        )
        self.assertEqual(ContradictionEngine().detect(item), [])

    def test_compatible_footprint_creates_material_candidate(self):
        item = state()
        item.claims.append(
            Claim(
                claim_text="70 acres tillable",
                claim_type="tillable_acres",
                source_id="listing",
                extraction_confidence=0.9,
            )
        )
        item.evidence.append(
            Evidence(
                source_type=SourceType.DERIVED,
                source=EvidenceSource(publisher="System", dataset="footprint"),
                field_name="cultivated_acres",
                value=60,
                semantic_scope="property cultivated footprint",
                geometry={"type": "Polygon", "coordinates": []},
            )
        )
        result = ContradictionEngine().detect(item)[0]
        self.assertEqual(MaterialityEngine().assess(item, result), Materiality.HIGH)
