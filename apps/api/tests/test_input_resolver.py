import unittest

from app.investigation.input_resolver import (
    extract_address_candidate,
    extract_buyer_objectives,
    extract_claims,
    parse_number,
)


class InputExtractionTests(unittest.TestCase):
    def test_extracts_material_claims(self):
        claims = extract_claims(
            "The seller says 70 acres tillable with excellent drainage and it is irrigated.",
            "input",
        )
        self.assertEqual(
            {x.claim_type for x in claims}, {"tillable_acres", "drainage", "irrigation"}
        )

    def test_price_suffix(self):
        self.assertEqual(parse_number("1.2", "M"), 1_200_000)

    def test_buyer_objectives(self):
        self.assertIn(
            "low flood risk",
            extract_buyer_objectives("I want row crop productivity and low flood risk"),
        )

    def test_location_candidate(self):
        self.assertEqual(
            extract_address_candidate("An 85-acre farm near Ames, IA listed for $1m"), "Ames, IA"
        )

    def test_generic_question_is_not_mistaken_for_address(self):
        self.assertIsNone(extract_address_candidate("What is the agricultural market generally?"))
