import unittest

from fastapi.testclient import TestClient

from app.domain.models import InputType, InvestigationState
from app.main import app
from app.world_model.repository import repository


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health(self):
        self.assertEqual(self.client.get("/health").json(), {"status": "ok"})

    def test_local_frontend_cors_preflight(self):
        response = self.client.options(
            "/api/investigations",
            headers={
                "Origin": "http://127.0.0.1:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers["access-control-allow-origin"], "http://127.0.0.1:3000"
        )

    def test_cors_preflights_do_not_consume_rate_limit(self):
        headers = {
            "Origin": "http://127.0.0.1:3000",
            "Access-Control-Request-Method": "GET",
        }
        responses = [
            self.client.options("/api/investigations", headers=headers) for _ in range(130)
        ]
        self.assertTrue(all(response.status_code == 200 for response in responses))

    def test_profile_roundtrip(self):
        created = self.client.post(
            "/api/buyer-profiles",
            json={"name": "Conservative buyer", "target_states": ["IA"], "risk_tolerance": "low"},
        )
        self.assertEqual(created.status_code, 201)
        fetched = self.client.get(f"/api/buyer-profiles/{created.json()['id']}")
        self.assertEqual(fetched.json()["name"], "Conservative buyer")
        updated = self.client.put(
            f"/api/buyer-profiles/{created.json()['id']}",
            json={"name": "Updated buyer", "target_states": ["IA", "IL"]},
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["name"], "Updated buyer")

    def test_trace_and_dossier_contracts(self):
        state = repository.save(
            InvestigationState(input_type=InputType.QUERY, raw_input="controlled farm")
        )
        trace = self.client.get(f"/api/investigations/{state.id}/trace")
        dossier = self.client.get(f"/api/investigations/{state.id}/dossier")
        self.assertEqual(trace.status_code, 200)
        self.assertIn("tool_calls", trace.json())
        self.assertEqual(dossier.status_code, 200)
        self.assertIn("claim_transition_history", dossier.json())
