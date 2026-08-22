import unittest

from app.connectors.agriculture import parse_cdl_result
from app.connectors.mireye import MireyeRESTAdapter


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

    def test_mireye_property_scope_requires_polygon_metadata(self):
        adapter = MireyeRESTAdapter()
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
