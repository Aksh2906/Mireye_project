import unittest
from uuid import uuid4

from app.domain.models import (
    Claim,
    Evidence,
    EvidenceSource,
    InputType,
    InvestigationState,
    ListingArtifact,
    Property,
    SourceType,
    ToolResult,
)
from app.investigation.orchestrator import InvestigationOrchestrator
from app.world_model.repository import repository


class FakeResolver:
    async def resolve(self, state):
        source = Evidence(
            source_type=SourceType.USER_PROVIDED,
            source=EvidenceSource(publisher="Test", dataset="Controlled input"),
            field_name="input_text",
            value=state.raw_input,
        )
        state.evidence.append(source)
        state.property = Property(
            address="Controlled Farm, IA",
            latitude=42.0,
            longitude=-93.0,
            acreage=100,
        )
        state.listing = ListingArtifact(asking_price=600_000)
        state.claims.append(
            Claim(
                claim_text="70 acres tillable",
                claim_type="tillable_acres",
                source_id=str(source.id),
                extraction_confidence=0.9,
            )
        )
        return state


class FakeMireye:
    async def fetch_context(self, latitude, longitude):
        return ToolResult(
            tool_name="mireye.fetch_context",
            success=True,
            observations=[
                Evidence(
                    source_type=SourceType.MIREYE,
                    source=EvidenceSource(publisher="Mireye", dataset="Controlled contract"),
                    field_name="physical_context",
                    value={"terrain": "controlled"},
                ),
                Evidence(
                    source_type=SourceType.MIREYE,
                    source=EvidenceSource(publisher="Mireye", dataset="Controlled contract"),
                    field_name="cultivated_acres",
                    value=70,
                    semantic_scope="property cultivated footprint",
                    geometry={"type": "Polygon", "coordinates": []},
                    confidence=0.8,
                ),
            ],
        )


class FakeAgriculture:
    async def get_crop_history(self, latitude, longitude, years):
        return ToolResult(
            tool_name="agriculture.get_crop_history",
            success=True,
            observations=[
                Evidence(
                    source_type=SourceType.USDA_CDL,
                    source=EvidenceSource(publisher="USDA NASS", dataset="CDL", vintage=str(year)),
                    field_name="crop_class",
                    value={"category": "Corn", "code": 1, "is_agricultural": True},
                )
                for year in years
            ],
        )

    async def get_soil_context(self, latitude, longitude):
        return ToolResult(
            tool_name="agriculture.get_soil_context",
            success=True,
            observations=[
                Evidence(
                    source_type=SourceType.USDA_SSURGO,
                    source=EvidenceSource(publisher="USDA NRCS", dataset="SSURGO"),
                    field_name="soil_context",
                    value=[{"drainage": "controlled"}],
                )
            ],
        )


class FakeMarket:
    async def get_benchmark(self, state, county):
        return ToolResult(
            tool_name="market.get_benchmark",
            success=True,
            observations=[
                Evidence(
                    source_type=SourceType.MARKET_DATA,
                    source=EvidenceSource(publisher="Controlled", dataset="Benchmark"),
                    field_name="value_per_acre",
                    value=7_000,
                    unit="USD/acre",
                    confidence=0.8,
                )
            ],
        )

    async def find_comparables(self, state, county, acreage):
        return ToolResult(
            tool_name="market.find_comparables",
            success=True,
            observations=[
                Evidence(
                    source_type=SourceType.MARKET_DATA,
                    source=EvidenceSource(publisher="Controlled", dataset="Comparable sales"),
                    field_name="comparable_value_per_acre",
                    value=6_900,
                    unit="USD/acre",
                    confidence=0.75,
                    raw_reference={
                        "comparable": {
                            "location": "Controlled County, IA",
                            "sale_price": 690_000,
                            "acreage": 100,
                            "sale_date": "2026-01-01",
                        }
                    },
                )
            ],
        )


class EndToEndTests(unittest.IsolatedAsyncioTestCase):
    async def test_query_to_evidence_decision_and_strategy(self):
        state = InvestigationState(
            id=uuid4(),
            input_type=InputType.QUERY,
            raw_input="Controlled 100-acre Iowa farm",
        )
        repository.save(state)
        orchestrator = InvestigationOrchestrator()
        orchestrator.resolver = FakeResolver()
        orchestrator.mireye = FakeMireye()
        orchestrator.agriculture = FakeAgriculture()
        orchestrator.market = FakeMarket()
        orchestrator.settings = orchestrator.settings.model_copy(
            update={
                "market_benchmark_url": "https://market.test/benchmark",
                "market_comparables_url": "https://market.test/comparables",
            }
        )
        await orchestrator.run(state.id)
        result = repository.get(state.id)
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.status, "completed")
        self.assertEqual(result.decision.verdict, "ACQUIRE")
        self.assertTrue(result.valuation.evidence_ids)
        self.assertTrue(result.diligence)
        self.assertTrue(result.negotiation)
        self.assertGreaterEqual(len(result.tool_calls), 4)
        self.assertTrue(any(signal.name == "Agricultural continuity" for signal in result.signals))
        self.assertEqual(result.claims[0].state, "PARTIALLY_SUPPORTED")
        self.assertTrue(result.claim_transitions)
        self.assertTrue(result.comparables)
        self.assertIsNotNone(result.decision_stability)
        self.assertEqual(result.decision_stability.classification, "PRICE_SENSITIVE")
