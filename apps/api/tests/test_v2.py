import unittest

from fastapi.testclient import TestClient

from app.agriculture.engine import AgricultureOpportunityEngine, HazardIntelligenceEngine
from app.connectors.geospatial import BoundaryService, BoundaryValidationError
from app.connectors.listing_providers import MockListingAdapter, NormalizedListing
from app.domain.models import (
    BuyerObjective,
    CreateInvestigationRequest,
    Evidence,
    EvidenceSource,
    InputType,
    InvestigationState,
    ListingArtifact,
    Property,
    SourceType,
)
from app.investigation.input_resolver import extract_buyer_objective
from app.investigation.metrics import calculate_behavior_metrics
from app.investigation.v2 import HypothesisEngine
from app.main import app
from app.opportunities.engine import OpportunityDiscoveryEngine


def evidence(
    field, value, *, source=SourceType.USDA_AG_STATISTICS, activity="corn", confidence=0.8
):
    return Evidence(
        source_type=source,
        source=EvidenceSource(publisher="Controlled", dataset="V2 fixture", vintage="2025"),
        field_name=field,
        value=value,
        confidence=confidence,
        semantic_scope="Iowa regional assumption",
        raw_reference={"activity": activity},
    )


class V2DomainTests(unittest.TestCase):
    def test_structured_input_contract_normalizes(self):
        request = CreateInvestigationRequest.model_validate(
            {
                "input": {"type": "location", "latitude": 42.0, "longitude": -93.0},
                "objective": {"objective": "crop", "risk_tolerance": "low"},
            }
        )
        self.assertEqual(request.input_type, InputType.LOCATION)
        self.assertEqual(request.input, "42.0,-93.0")
        self.assertEqual(request.objective.objective, "crop")

    def test_requirement_extraction_validates_numeric_objective(self):
        objective = extract_buyer_objective(
            "I want 50-100 acres within 25 miles. Budget is $750k for cattle grazing; low risk."
        )
        self.assertEqual(objective.budget.acquisition_max, 750_000)
        self.assertEqual(objective.acreage.minimum, 50)
        self.assertEqual(objective.acreage.maximum, 100)
        self.assertEqual(objective.geography.max_distance_miles, 25)
        self.assertIn("grazing", objective.agricultural_activities)

    def test_boundary_area_and_closure(self):
        result = BoundaryService().validate(
            {
                "type": "Polygon",
                "coordinates": [[[-93.0, 42.0], [-92.99, 42.0], [-92.99, 42.01], [-93.0, 42.01]]],
            }
        )
        self.assertGreater(result["area_acres"], 100)
        ring = result["geometry"]["coordinates"][0]
        self.assertEqual(ring[0], ring[-1])
        self.assertFalse(result["is_legal_boundary"])

    def test_boundary_rejects_point(self):
        with self.assertRaises(BoundaryValidationError):
            BoundaryService().validate({"type": "Point", "coordinates": [-93, 42]})

    def test_economics_requires_all_sourced_inputs(self):
        state = InvestigationState(
            input_type="query",
            raw_input="farm",
            property=Property(acreage=100),
            listing=ListingArtifact(asking_price=600_000),
            evidence=[evidence("yield_per_acre", 190)],
        )
        AgricultureOpportunityEngine().evaluate(state)
        self.assertFalse(any(item.economic_scenarios for item in state.crop_opportunities))

    def test_three_scenario_economics_and_break_even(self):
        state = InvestigationState(
            input_type="query",
            raw_input="corn farm",
            property=Property(acreage=100),
            listing=ListingArtifact(asking_price=600_000),
            evidence=[
                evidence("yield_per_acre", 190),
                evidence("commodity_price", 5.0),
                evidence("operating_cost_per_acre", 550),
                evidence(
                    "crop_class",
                    {"category": "Corn", "is_agricultural": True},
                    source=SourceType.USDA_CDL,
                ),
            ],
        )
        AgricultureOpportunityEngine().evaluate(state)
        corn = next(item for item in state.crop_opportunities if item.crop == "corn")
        self.assertEqual(
            [item.name for item in corn.economic_scenarios], ["conservative", "base", "optimistic"]
        )
        self.assertGreater(corn.economic_scenarios[1].annual_operating_profit, 0)
        self.assertIsNotNone(corn.economic_scenarios[1].break_even_yield)
        self.assertIsNotNone(corn.economic_scenarios[1].break_even_price)
        self.assertTrue(all(item.assumptions for item in corn.economic_scenarios))

    def test_activity_specific_hazard_translation(self):
        state = InvestigationState(
            input_type="query",
            raw_input="grazing",
            user_objective=BuyerObjective(agricultural_activities=["grazing"]),
            evidence=[evidence("flood_exposure", "high", source=SourceType.MIREYE)],
        )
        HazardIntelligenceEngine().evaluate(state)
        self.assertEqual(state.hazard_assessments[0].materiality, "HIGH")
        self.assertIn("grazing", state.hazard_assessments[0].relevant_activities)
        self.assertTrue(state.hazard_assessments[0].agricultural_consequences)

    def test_hypotheses_are_explicit_and_objective_sensitive(self):
        state = InvestigationState(
            input_type="query",
            raw_input="premium land",
            user_objective=BuyerObjective(willingness_to_pay_premium=True),
        )
        HypothesisEngine().initialize(state)
        self.assertGreaterEqual(len(state.hypotheses), 5)
        self.assertTrue(any("premium" in item.statement.casefold() for item in state.hypotheses))

    def test_decision_relevant_evidence_ratio_is_observable(self):
        state = InvestigationState(input_type="query", raw_input="farm")
        state.evidence = [evidence("commodity_price", 5), evidence("decorative_field", "x")]
        state.valuation = None
        metrics = calculate_behavior_metrics(state)
        self.assertEqual(metrics["decision_relevant_evidence_ratio"], 0)


class V2ApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_agriculture_endpoint_refuses_to_infer_without_evidence(self):
        response = self.client.post(
            "/api/agriculture/evaluate",
            json={"latitude": 42, "longitude": -93, "acreage": 80, "purchase_price": 500000},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["limitations"])
        self.assertFalse(body["economic_scenarios"])

    def test_opportunity_search_degrades_explicitly(self):
        response = self.client.post(
            "/api/opportunities/search",
            json={"latitude": 42, "longitude": -93, "radius_miles": 10},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "unavailable")
        self.assertEqual(response.json()["alternatives"], [])


class OpportunityTests(unittest.IsolatedAsyncioTestCase):
    async def test_adaptive_search_and_objective_screening(self):
        provider = MockListingAdapter(
            [
                NormalizedListing(
                    id=str(index),
                    source="fixture",
                    source_url=f"https://example.test/{index}",
                    title=f"Farm {index}",
                    price=500_000 + index * 10_000,
                    acreage=70 + index,
                    latitude=42 + index * 0.01,
                    longitude=-93,
                )
                for index in range(3)
            ]
        )
        objective = BuyerObjective.model_validate(
            {"budget": {"acquisition_max": 600_000}, "acreage": {"minimum": 50}}
        )
        alternatives, radii = await OpportunityDiscoveryEngine(provider).search(42, -93, objective)
        self.assertEqual(radii, [10])
        self.assertEqual(len(alternatives), 3)
        self.assertTrue(all(item.investigation_depth == "screened" for item in alternatives))


if __name__ == "__main__":
    unittest.main()
