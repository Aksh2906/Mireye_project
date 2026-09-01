import unittest

from app.connectors.agriculture import parse_cdl_result
from app.connectors.listing_providers import RentCastListingAdapter
from app.connectors.market import NASS_LAND_VALUE_SERIES, select_latest_nass_land_value
from app.connectors.mireye import MireyeMCPAdapter


class ConnectorNormalizationTests(unittest.TestCase):
    def test_cdl_result_shape_is_parsed(self):
        result = parse_cdl_result(
            '<Result>{x: 1, y: 2, value: 1, category: "Corn", color: "#FFD400"}</Result>'
        )
        self.assertEqual(result, {"code": 1, "category": "Corn", "is_agricultural": True})

    def test_non_agricultural_cdl_class_is_explicit(self):
        result = parse_cdl_result(
            '<Result>{value: 111, category: "Open Water", color: "#0000ff"}</Result>'
        )
        self.assertIsNotNone(result)
        self.assertFalse(result["is_agricultural"])

    def test_developed_medium_intensity_is_not_agricultural(self):
        result = parse_cdl_result(
            '<Result>{value: 123, category: "Developed/Medium Intensity"}</Result>'
        )
        self.assertIsNotNone(result)
        self.assertFalse(result["is_agricultural"])

    def test_latest_nass_land_value_is_selected_and_parsed(self):
        selected = select_latest_nass_land_value(
            [
                {"short_desc": NASS_LAND_VALUE_SERIES, "year": 2024, "Value": "9,420"},
                {"short_desc": NASS_LAND_VALUE_SERIES, "year": 2025, "Value": "9,780"},
                {"short_desc": "OTHER SERIES", "year": 2026, "Value": "99,999"},
            ]
        )
        self.assertIsNotNone(selected)
        assert selected is not None
        row, value = selected
        self.assertEqual(row["year"], 2025)
        self.assertEqual(value, 9780)

    def test_suppressed_nass_values_are_ignored(self):
        selected = select_latest_nass_land_value(
            [{"short_desc": NASS_LAND_VALUE_SERIES, "year": 2025, "Value": "(D)"}]
        )
        self.assertIsNone(selected)

    def test_mireye_property_scope_requires_polygon_metadata(self):
        adapter = MireyeMCPAdapter()
        evidence = adapter._normalize_context(
            "property_context",
            {"latitude": 42, "longitude": -93},
            {
                "structuredContent": {
                    "cultivated_acres": 70,
                    "metadata": {"scope": "property"},
                    "geometry": {"type": "Polygon", "coordinates": []},
                }
            },
            42,
            -93,
        )
        acres = next(item for item in evidence if item.field_name == "cultivated_acres")
        self.assertEqual(acres.semantic_scope, "property cultivated footprint")
        self.assertEqual(acres.raw_reference["provider_field"], "cultivated_acres")

    def test_mireye_markdown_text_is_preserved(self):
        payload = MireyeMCPAdapter._structured_payload(
            {"content": [{"type": "text", "text": "# Site report\n\n- Well drained"}]}
        )
        self.assertEqual(payload, "# Site report\n\n- Well drained")

    def test_mireye_rest_answer_is_normalized_as_report(self):
        adapter = MireyeMCPAdapter()
        adapter.settings.mireye_api_url = "https://api.mireye.com"
        evidence = adapter._normalize_rest_answer(
            {
                "answer": "## Soil\n\nModerately drained.",
                "confidence": "HIGH",
                "citations": [{"source": "USDA"}],
            },
            42,
            -93,
        )
        self.assertEqual(evidence[0].field_name, "mireye_report")
        self.assertEqual(evidence[0].value, "## Soil\n\nModerately drained.")
        self.assertEqual(evidence[0].raw_reference["citations"], [{"source": "USDA"}])

    def test_empty_mireye_narrative_becomes_curated_structured_evidence(self):
        adapter = MireyeMCPAdapter()
        adapter.settings.mireye_api_url = "https://api.mireye.com"
        evidence = adapter._normalize_rest_answer(
            {
                "answer": "",
                "fields_used": ["slope_degrees"],
                "citations": [{"source": "USGS"}],
                "data_gaps": [{"field": "water", "reason": "unavailable"}],
                "trace": {"planner_reasoning": "must not be a primary evidence value"},
            },
            42,
            -93,
        )
        self.assertIsInstance(evidence[0].value, dict)
        self.assertNotIn("trace", evidence[0].value)
        self.assertEqual(evidence[0].value["fields_used"], ["slope_degrees"])

    def test_nested_mireye_json_answer_is_structured(self):
        adapter = MireyeMCPAdapter()
        adapter.settings.mireye_api_url = "https://api.mireye.com"
        evidence = adapter._normalize_rest_answer(
            {
                "answer": '{"confidence":"high","fields_used":["fema_flood_zone"],"data_gaps":[]}',
                "confidence": "low",
            },
            42,
            -93,
        )
        self.assertIsInstance(evidence[0].value, dict)
        self.assertEqual(evidence[0].value["fields_used"], ["fema_flood_zone"])
        self.assertEqual(evidence[0].confidence, 0.85)

    def test_mireye_fetch_fields_preserve_provenance_and_partial_failures(self):
        adapter = MireyeMCPAdapter()
        adapter.settings.mireye_api_url = "https://api.mireye.com"
        evidence, limitations = adapter._normalize_fetch_payload(
            {
                "fetched_at": "2026-08-31T00:00:00Z",
                "fields": {
                    "within_floodplain_polygon": {
                        "value": False,
                        "unit": None,
                        "source": "FEMA NFHL",
                        "source_url": "https://www.fema.gov/flood-maps",
                        "confidence": "high",
                        "dataset_vintage": "2025",
                        "status": "ok",
                    },
                    "parcel_boundary_geojson": {
                        "status": "failed",
                        "error": "provider quota reached",
                    },
                },
            },
            42,
            -93,
        )
        self.assertEqual(len(evidence), 1)
        self.assertEqual(evidence[0].field_name, "within_floodplain_polygon")
        self.assertFalse(evidence[0].value)
        self.assertEqual(evidence[0].source.dataset, "FEMA NFHL")
        self.assertEqual(evidence[0].raw_reference["endpoint"], "/v1/fetch")
        self.assertIn("provider quota reached", limitations[0])

    def test_rentcast_land_listing_is_normalized(self):
        listing = RentCastListingAdapter().normalize(
            {
                "id": "farm-1",
                "formattedAddress": "100 Farm Rd, Ames, IA 50010",
                "propertyType": "Land",
                "status": "Active",
                "price": 1_200_000,
                "lotSize": 85 * 43560,
                "latitude": 42.03,
                "longitude": -93.62,
                "lastSeenDate": "2026-08-30T00:00:00Z",
            }
        )
        self.assertEqual(listing.acreage, 85)
        self.assertEqual(listing.source, "RentCast sale listings")
        self.assertEqual(listing.geometry.coordinates, [-93.62, 42.03])
