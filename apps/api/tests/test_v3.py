import unittest

from fastapi.testclient import TestClient

from app.agriculture.engine import (
    ACTIVITY_REGISTRY,
    AgricultureOpportunityEngine,
    HazardIntelligenceEngine,
)
from app.agriculture.finance import InvestmentEconomicsEngine
from app.connectors.geospatial import BoundaryService
from app.connectors.listing_providers import MockListingAdapter, NormalizedListing
from app.domain.models import (
    ActivityCategory,
    BoundaryKind,
    BuyerObjective,
    Evidence,
    EvidenceSource,
    FinancialInputs,
    InputType,
    InvestigationState,
    ListingArtifact,
    Property,
    SourceType,
    ToolResult,
)
from app.main import app
from app.opportunities.engine import OpportunityDiscoveryEngine
from app.world_model.repository import repository


def economic_evidence(field: str, value: float, activity: str = "corn") -> Evidence:
    return Evidence(
        source_type=SourceType.USDA_AG_STATISTICS,
        source=EvidenceSource(
            publisher="Controlled",
            dataset="Regional enterprise budget",
            vintage="2026",
        ),
        field_name=field,
        value=value,
        confidence=0.82,
        semantic_scope="Regional planning assumption",
        raw_reference={"activity": activity},
    )


class V3EngineTests(unittest.TestCase):
    def test_boundary_record_preserves_provenance_and_acreage_delta(self):
        record = BoundaryService().build_record(
            {
                "type": "Polygon",
                "coordinates": [[[-93.0, 42.0], [-92.99, 42.0], [-92.99, 42.01], [-93.0, 42.01]]],
            },
            kind=BoundaryKind.USER_UPLOADED,
            source_name="Buyer GeoJSON",
            claimed_acres=100,
            confidence=0.9,
        )
        self.assertEqual(record.source_name, "Buyer GeoJSON")
        self.assertGreater(record.area_acres, 100)
        self.assertIsNotNone(record.acreage_difference_percent)
        self.assertFalse(record.is_legal_boundary)

    def test_generated_analysis_area_matches_claimed_acreage_but_is_explicitly_approximate(self):
        record = BoundaryService().generate_analysis_geometry(42, -93, 85)
        self.assertEqual(record.kind, BoundaryKind.ANALYSIS)
        self.assertAlmostEqual(record.area_acres, 85, delta=0.2)
        self.assertLess(record.confidence, 0.5)
        self.assertTrue(any("does not indicate parcel" in item for item in record.limitations))

    def test_multi_year_finance_produces_npv_irr_dscr_and_decision(self):
        state = InvestigationState(
            input_type=InputType.QUERY,
            raw_input="corn farm",
            property=Property(acreage=100),
            listing=ListingArtifact(asking_price=400_000),
            user_objective=BuyerObjective(return_target=0.05),
            financial_inputs=FinancialInputs(
                down_payment_percent=0.4,
                interest_rate=0.05,
                annual_property_tax=4_000,
                annual_insurance=2_000,
                time_horizon_years=10,
            ),
            evidence=[
                economic_evidence("yield_per_acre", 210),
                economic_evidence("commodity_price", 6.0),
                economic_evidence("operating_cost_per_acre", 500),
                Evidence(
                    source_type=SourceType.USDA_CDL,
                    source=EvidenceSource(publisher="USDA", dataset="CDL", vintage="2025"),
                    field_name="crop_class",
                    value={"category": "Corn", "is_agricultural": True},
                    confidence=0.8,
                ),
            ],
        )
        AgricultureOpportunityEngine().evaluate(state)
        HazardIntelligenceEngine().evaluate(state)
        InvestmentEconomicsEngine().enrich(state)
        base = next(item for item in state.economic_scenarios if item.name == "base")
        self.assertEqual(len(base.cash_flows), 11)
        self.assertIsNotNone(base.npv)
        self.assertIsNotNone(base.irr)
        self.assertIsNotNone(base.debt_service_coverage_ratio)
        self.assertIsNotNone(state.investment_decision)
        self.assertIn(state.investment_decision.label, {"Buy", "Investigate", "Negotiate"})

    def test_hazard_stress_is_explicit_and_activity_specific(self):
        state = InvestigationState(
            input_type=InputType.QUERY,
            raw_input="dairy",
            user_objective=BuyerObjective(agricultural_activities=[ActivityCategory.DAIRY]),
            evidence=[
                Evidence(
                    source_type=SourceType.HAZARD,
                    source=EvidenceSource(
                        publisher="Controlled hazard source",
                        dataset="Flood exposure",
                        vintage="2026",
                    ),
                    field_name="flood_exposure",
                    value={"level": "high", "affected_area_acres": 12},
                    confidence=0.85,
                )
            ],
        )
        HazardIntelligenceEngine().evaluate(state)
        hazard = state.hazard_assessments[0]
        self.assertEqual(hazard.annual_profit_stress, 0.2)
        self.assertEqual(hazard.affected_area_acres, 12)
        self.assertIn("dairy", hazard.relevant_activities)
        self.assertTrue(hazard.mitigation_actions)

    def test_dairy_economics_uses_herd_units_not_acres(self):
        state = InvestigationState(
            input_type=InputType.QUERY,
            raw_input="dairy farm",
            property=Property(acreage=200),
            listing=ListingArtifact(asking_price=1_000_000),
            user_objective=BuyerObjective(agricultural_activities=[ActivityCategory.DAIRY]),
            evidence=[
                economic_evidence("herd_size", 100, "dairy"),
                economic_evidence("milk_yield_per_head", 20_000, "dairy"),
                economic_evidence("price_per_unit", 0.22, "dairy"),
                economic_evidence("operating_cost_per_head", 3_000, "dairy"),
            ],
        )
        AgricultureOpportunityEngine().evaluate(state)
        dairy = next(item for item in state.activity_opportunities if item.activity == "dairy")
        base = next(item for item in dairy.economic_scenarios if item.name == "base")
        self.assertEqual(base.annual_revenue, 440_000)
        self.assertEqual(base.annual_operating_cost, 300_000)

    def test_activity_registry_goes_beyond_row_crops(self):
        activities = {item.category for item in ACTIVITY_REGISTRY}
        self.assertTrue(
            {
                ActivityCategory.DAIRY,
                ActivityCategory.CATTLE,
                ActivityCategory.GRAZING,
                ActivityCategory.ORCHARD,
                ActivityCategory.GREENHOUSE,
                ActivityCategory.SOLAR,
                ActivityCategory.WIND,
                ActivityCategory.SHEEP,
                ActivityCategory.GOAT,
                ActivityCategory.MIXED,
            }.issubset(activities)
        )


class V3OpportunityTests(unittest.IsolatedAsyncioTestCase):
    async def test_search_deduplicates_and_ranks_candidates(self):
        provider = MockListingAdapter(
            [
                NormalizedListing(
                    id="a",
                    source="fixture",
                    source_url="https://example.test/a",
                    title="Closer farm",
                    price=500_000,
                    acreage=100,
                    latitude=42.01,
                    longitude=-93,
                ),
                NormalizedListing(
                    id="b",
                    source="fixture",
                    source_url="https://example.test/b",
                    title="Lower price per acre",
                    price=450_000,
                    acreage=110,
                    latitude=42.02,
                    longitude=-93,
                ),
                NormalizedListing(
                    id="c",
                    source="fixture",
                    source_url="https://example.test/c",
                    title="Third farm",
                    price=550_000,
                    acreage=90,
                    latitude=42.03,
                    longitude=-93,
                ),
            ]
        )
        objective = BuyerObjective.model_validate(
            {"budget": {"acquisition_max": 600_000}, "acreage": {"minimum": 80}}
        )
        alternatives, radii = await OpportunityDiscoveryEngine(provider).search(42, -93, objective)
        self.assertEqual(radii, [10])
        self.assertEqual(len(alternatives), 3)
        self.assertEqual(alternatives[0].title, "Lower price per acre")
        self.assertEqual(alternatives[0].recommendation, "deep_analysis")
        self.assertGreater(alternatives[0].distance_miles, 0)


class V3ApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_boundary_and_financial_inputs_roundtrip(self):
        state = repository.save(
            InvestigationState(
                input_type=InputType.LOCATION,
                raw_input="42,-93",
                property=Property(latitude=42, longitude=-93, acreage=120),
                listing=ListingArtifact(asking_price=600_000),
            )
        )
        boundary = self.client.post(
            f"/api/investigations/{state.id}/boundary",
            json={
                "kind": "user_uploaded",
                "source_name": "Uploaded GeoJSON",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[-93, 42], [-92.99, 42], [-92.99, 42.01], [-93, 42.01]]],
                },
            },
        )
        self.assertEqual(boundary.status_code, 200)
        self.assertEqual(boundary.json()["boundary"]["kind"], "user_uploaded")
        financials = self.client.post(
            f"/api/investigations/{state.id}/financial-inputs",
            json={"financial_inputs": {"interest_rate": 0.06, "time_horizon_years": 15}},
        )
        self.assertEqual(financials.status_code, 200)
        self.assertEqual(financials.json()["financial_inputs"]["interest_rate"], 0.06)

    def test_hazard_action_preserves_unavailable_state(self):
        state = repository.save(
            InvestigationState(
                input_type=InputType.LOCATION,
                raw_input="42,-93",
                property=Property(latitude=42, longitude=-93),
            )
        )

        class UnavailableMireye:
            async def fetch_context(self, latitude, longitude, fields=None):
                return ToolResult(
                    tool_name="mireye.fetch_context",
                    success=False,
                    limitations=["Mireye unavailable in controlled test."],
                )

        from app.investigation.orchestrator import orchestrator

        original = orchestrator.mireye
        orchestrator.mireye = UnavailableMireye()
        try:
            response = self.client.post(f"/api/investigations/{state.id}/actions/analyze-hazards")
        finally:
            orchestrator.mireye = original
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "unavailable")
        self.assertTrue(response.json()["limitations"])

    def test_hazard_action_uses_mireye_as_primary_source(self):
        state = repository.save(
            InvestigationState(
                input_type=InputType.LOCATION,
                raw_input="42,-93",
                property=Property(latitude=42, longitude=-93),
            )
        )

        class ControlledMireye:
            async def fetch_context(self, latitude, longitude, fields=None):
                return ToolResult(
                    tool_name="mireye.fetch_context",
                    success=True,
                    observations=[
                        Evidence(
                            source_type=SourceType.MIREYE,
                            source=EvidenceSource(
                                publisher="Mireye", dataset="Hazard Intelligence"
                            ),
                            field_name="fema_flood_zone",
                            value={"level": "moderate"},
                            confidence=0.8,
                        )
                    ],
                )

        from app.investigation.orchestrator import orchestrator

        original = orchestrator.mireye
        orchestrator.mireye = ControlledMireye()
        try:
            response = self.client.post(f"/api/investigations/{state.id}/actions/analyze-hazards")
        finally:
            orchestrator.mireye = original
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "completed")
        self.assertEqual(response.json()["sources"]["mireye"], "completed")
        self.assertEqual(response.json()["hazard_assessments"][0]["hazard"], "flood")

    def test_user_enterprise_budget_produces_readable_scenarios(self):
        state = repository.save(
            InvestigationState(
                input_type=InputType.LOCATION,
                raw_input="42,-93",
                property=Property(latitude=42, longitude=-93, acreage=100),
                listing=ListingArtifact(asking_price=500_000),
                user_objective=BuyerObjective(agricultural_activities=[ActivityCategory.ROW_CROP]),
            )
        )
        response = self.client.post(
            f"/api/investigations/{state.id}/economic-assumptions",
            json={
                "activity": "corn",
                "production_per_unit": 200,
                "price_per_unit": 5.25,
                "operating_cost_per_unit": 600,
                "source_name": "Controlled extension budget",
                "vintage": "2026",
                "geography": "Iowa planning region",
            },
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(len(body["economic_scenarios"]), 3)
        self.assertIsNotNone(body["investment_decision"])


if __name__ == "__main__":
    unittest.main()
