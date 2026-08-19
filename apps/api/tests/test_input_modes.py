import unittest

from app.domain.models import (
    Evidence,
    EvidenceSource,
    InputType,
    InvestigationState,
    ListingArtifact,
    Property,
    SourceType,
)
from app.investigation.input_resolver import InputResolver


class FakeGeocoder:
    async def resolve(self, address):
        return (
            Property(address=address, latitude=42, longitude=-93, state="Iowa"),
            [
                Evidence(
                    source_type=SourceType.GEOCODER,
                    source=EvidenceSource(publisher="Test", dataset="Geocoder"),
                    field_name="resolved_location",
                    value=address,
                )
            ],
            [],
        )


class FakeListing:
    async def fetch(self, url):
        artifact = ListingArtifact(
            url=url,
            raw_text="80 acres near Ames, IA listed for $640k with 70 acres tillable",
        )
        evidence = Evidence(
            source_type=SourceType.LISTING,
            source=EvidenceSource(publisher="Test", dataset="Listing"),
            field_name="listing_text",
            value=artifact.raw_text,
        )
        return artifact, [evidence]


class InputModeNormalizationTests(unittest.IsolatedAsyncioTestCase):
    async def test_all_input_modes_produce_same_property_contract(self):
        resolver = InputResolver(geocoder=FakeGeocoder(), listing=FakeListing())
        states = [
            InvestigationState(input_type=InputType.ADDRESS, raw_input="Ames, IA"),
            InvestigationState(
                input_type=InputType.LISTING_URL, raw_input="https://example.test/farm"
            ),
            InvestigationState(
                input_type=InputType.QUERY,
                raw_input="80 acres near Ames, IA listed for $640k with 70 acres tillable",
            ),
        ]
        for state in states:
            await resolver.resolve(state)
            self.assertIsInstance(state.property, Property)
            self.assertEqual(state.property.latitude, 42)
            self.assertEqual(state.property.longitude, -93)
            self.assertTrue(state.evidence)
        self.assertEqual(states[1].property.acreage, 80)
        self.assertEqual(states[2].property.acreage, 80)
        self.assertEqual(states[1].claims[0].claim_type, "tillable_acres")
