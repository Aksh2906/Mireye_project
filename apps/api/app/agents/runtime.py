from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.domain.models import AgentAssessment, Hypothesis, InvestigationState
from app.investigation.engines import InvestigationCandidate

PROMPT_DIR = Path(__file__).resolve().parents[1] / "prompts"


class AgentRuntime:
    """The only application boundary allowed to invoke OpenAI."""

    def __init__(self) -> None:
        self.settings = get_settings()

    def _summary(self, state: InvestigationState) -> dict[str, Any]:
        return {
            "property": state.property.model_dump(mode="json") if state.property else None,
            "buyer": state.buyer_snapshot.model_dump(mode="json") if state.buyer_snapshot else None,
            "objective": state.user_objective.model_dump(mode="json"),
            "hypotheses": [item.model_dump(mode="json") for item in state.hypotheses],
            "claims": [item.model_dump(mode="json") for item in state.claims],
            "evidence": [
                {
                    "id": str(item.id),
                    "source_type": item.source_type,
                    "field": item.field_name,
                    "value": item.value,
                    "confidence": item.confidence,
                    "limitations": item.limitations,
                    "spatial_resolution": item.spatial_resolution,
                    "temporal_resolution": item.temporal_resolution,
                }
                for item in state.evidence
            ],
            "contradictions": [item.model_dump(mode="json") for item in state.contradictions],
            "unknowns": [item.model_dump(mode="json") for item in state.unknowns],
            "valuation": state.valuation.model_dump(mode="json") if state.valuation else None,
            "agricultural_opportunities": [
                item.model_dump(mode="json") for item in state.activity_opportunities
            ],
            "hazards": [item.model_dump(mode="json") for item in state.hazard_assessments],
            "alternatives": [item.model_dump(mode="json") for item in state.alternatives],
            "limitations": state.limitations,
        }

    async def _structured(
        self, prompt_name: str, payload: dict[str, Any], schema: dict[str, Any]
    ) -> dict[str, Any] | None:
        if not self.settings.openai_api_key:
            return None
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=self.settings.openai_api_key)
            request: dict[str, Any] = {
                "model": self.settings.openai_model,
                "instructions": (PROMPT_DIR / prompt_name).read_text(),
                "input": json.dumps(payload, default=str),
                "reasoning": {"effort": self.settings.openai_reasoning_effort},
                "text": {
                    "format": {
                        "type": "json_schema",
                        "name": "agent_output",
                        "strict": True,
                        "schema": schema,
                    }
                },
            }
            response = await client.responses.create(**request)
            return json.loads(response.output_text)
        except Exception:
            return None

    async def propose_investigations(
        self, state: InvestigationState, available: list[str]
    ) -> list[InvestigationCandidate]:
        schema = {
            "type": "object",
            "additionalProperties": False,
            "required": ["candidates"],
            "properties": {
                "candidates": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": [
                            "name",
                            "expected_decision_improvement",
                            "materiality",
                            "uncertainty",
                            "reliability",
                            "cost",
                            "rationale",
                        ],
                        "properties": {
                            "name": {"type": "string", "enum": available},
                            "expected_decision_improvement": {
                                "type": "number",
                                "minimum": 0,
                                "maximum": 1,
                            },
                            "materiality": {"type": "number", "minimum": 0, "maximum": 1},
                            "uncertainty": {"type": "number", "minimum": 0, "maximum": 1},
                            "reliability": {"type": "number", "minimum": 0, "maximum": 1},
                            "cost": {"type": "number", "minimum": 0, "maximum": 1},
                            "rationale": {"type": "string"},
                        },
                    },
                }
            },
        }
        result = await self._structured(
            "orchestrator.md", {"state": self._summary(state), "available_tools": available}, schema
        )
        if result:
            return [InvestigationCandidate(**item) for item in result["candidates"]]
        defaults = {
            "mireye.fetch_context": (
                0.8,
                0.8,
                0.9,
                0.75,
                0.08,
                "Establish independent physical context.",
            ),
            "agriculture.get_crop_history": (
                0.85,
                0.9,
                0.9,
                0.7,
                0.03,
                "Test the agricultural-use narrative over time.",
            ),
            "agriculture.get_soil_context": (
                0.7,
                0.75,
                0.8,
                0.7,
                0.03,
                "Investigate soil and drainage context.",
            ),
            "agriculture.get_economics": (
                0.95,
                1.0,
                1.0,
                0.75,
                0.06,
                "Retrieve sourced yield, price, cost, and infrastructure assumptions for activity economics.",
            ),
            "market.get_benchmark": (
                0.9,
                1.0,
                1.0,
                0.65,
                0.05,
                "Bound the property's economic indication.",
            ),
            "market.find_comparables": (
                0.82,
                0.9,
                0.9,
                0.72,
                0.08,
                "Test the benchmark against traceable comparable transactions.",
            ),
            "hazard.get_context": (
                0.88,
                0.95,
                0.9,
                0.75,
                0.05,
                "Test activity-specific disaster exposure and downside economics.",
            ),
            "listing.search": (
                0.7,
                0.8,
                0.8,
                0.65,
                0.08,
                "Search nearby alternatives when they could change the acquisition decision.",
            ),
        }
        activities = {item.value for item in state.user_objective.agricultural_activities}
        if activities & {"grazing", "cattle", "dairy"}:
            defaults["mireye.fetch_context"] = (
                0.92,
                0.95,
                0.9,
                0.75,
                0.08,
                "Test terrain, water, access, hazard, and infrastructure assumptions for livestock use.",
            )
        if state.user_objective.objective.value in {"maximize_profit", "investment"}:
            defaults["market.get_benchmark"] = (
                0.95,
                1.0,
                1.0,
                0.65,
                0.05,
                "Bound acquisition economics before deepening lower-impact physical questions.",
            )
        return [
            InvestigationCandidate(
                name=name,
                expected_decision_improvement=v[0],
                materiality=v[1],
                uncertainty=v[2],
                reliability=v[3],
                cost=v[4],
                rationale=v[5],
            )
            for name in available
            for v in [defaults[name]]
        ]

    async def propose_hypotheses(self, state: InvestigationState) -> list[Hypothesis]:
        schema = {
            "type": "object",
            "additionalProperties": False,
            "required": ["hypotheses"],
            "properties": {
                "hypotheses": {
                    "type": "array",
                    "maxItems": 6,
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["statement", "importance", "materiality"],
                        "properties": {
                            "statement": {"type": "string"},
                            "importance": {"type": "string", "enum": ["low", "medium", "high"]},
                            "materiality": {"type": "number", "minimum": 0, "maximum": 1},
                        },
                    },
                }
            },
        }
        result = await self._structured(
            "orchestrator.md",
            {
                "task": "Propose falsifiable, decision-relevant hypotheses only.",
                "state": self._summary(state),
            },
            schema,
        )
        return [Hypothesis(**item) for item in result["hypotheses"]] if result else []

    async def critique(self, state: InvestigationState) -> dict[str, Any]:
        schema = {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "assessment",
                "strongest_counterargument",
                "requires_investigation",
                "recommended_tool",
            ],
            "properties": {
                "assessment": {"type": "string"},
                "strongest_counterargument": {"type": "string"},
                "requires_investigation": {"type": "boolean"},
                "recommended_tool": {"type": ["string", "null"]},
            },
        }
        result = await self._structured("critic_agent.md", self._summary(state), schema)
        return result or {
            "assessment": "Automated critic could not run without the configured agent provider.",
            "strongest_counterargument": "Material provider evidence or valuation may remain unresolved.",
            "requires_investigation": False,
            "recommended_tool": None,
        }

    async def assess(self, state: InvestigationState, agent_name: str) -> AgentAssessment | None:
        prompts = {
            "property_intelligence": "property_agent.md",
            "agricultural_intelligence": "agriculture_agent.md",
            "market_valuation": "market_agent.md",
            "strategy": "strategy_agent.md",
        }
        schema = {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "assessment",
                "unknowns",
                "recommended_actions",
                "evidence_ids",
                "confidence",
            ],
            "properties": {
                "assessment": {"type": "string"},
                "unknowns": {"type": "array", "items": {"type": "string"}},
                "recommended_actions": {"type": "array", "items": {"type": "string"}},
                "evidence_ids": {"type": "array", "items": {"type": "string"}},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            },
        }
        result = await self._structured(prompts[agent_name], self._summary(state), schema)
        if not result:
            return None
        available = {str(item.id): item.id for item in state.evidence}
        evidence_ids = [available[value] for value in result["evidence_ids"] if value in available]
        return AgentAssessment(
            agent_name=agent_name,
            assessment=result["assessment"],
            unknowns=result["unknowns"],
            recommended_actions=result["recommended_actions"],
            evidence_ids=evidence_ids,
            confidence=result["confidence"],
        )
