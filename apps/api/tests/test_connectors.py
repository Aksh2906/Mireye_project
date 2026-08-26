import unittest

from app.connectors.agriculture import parse_cdl_result
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
