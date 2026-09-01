from __future__ import annotations

from app.config import get_settings
from app.connectors.http import async_client
from app.domain.models import Evidence, EvidenceSource, SourceType, ToolResult

ECONOMIC_FIELDS = {
    "yield_per_acre",
    "expected_yield",
    "production_per_unit",
    "milk_yield_per_head",
    "productive_units",
    "herd_size",
    "commodity_price",
    "price_per_unit",
    "operating_cost_per_acre",
    "operating_cost_per_unit",
    "operating_cost_per_head",
    "initial_infrastructure_cost",
    "required_improvement_cost",
    "transaction_cost",
}


class AgricultureEconomicsAdapter:
    """Normalizes a maintained regional enterprise-budget/economics service."""

    async def get_assumptions(
        self,
        *,
        state: str | None,
        county: str | None,
        activities: list[str],
        crops: list[str],
    ) -> ToolResult:
        settings = get_settings()
        if not settings.agriculture_economics_url:
            return ToolResult(
                tool_name="agriculture.get_economics",
                success=False,
                limitations=[],
            )
        headers = (
            {"Authorization": f"Bearer {settings.agriculture_economics_token}"}
            if settings.agriculture_economics_token
            else {}
        )
        try:
            async with async_client(timeout=60) as client:
                response = await client.post(
                    settings.agriculture_economics_url,
                    json={
                        "state": state,
                        "county": county,
                        "activities": activities,
                        "crops": crops,
                    },
                    headers=headers,
                )
                response.raise_for_status()
                payload = response.json()
        except Exception as exc:
            return ToolResult(
                tool_name="agriculture.get_economics",
                success=False,
                limitations=[f"Agricultural economics provider unavailable: {type(exc).__name__}"],
            )
        source = payload.get("source", {}) if isinstance(payload, dict) else {}
        rows = payload.get("assumptions", []) if isinstance(payload, dict) else []
        observations: list[Evidence] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            activity = str(row.get("activity") or "all").casefold()
            row_source = row.get("source", {})
            units_value = row.get("units")
            units: dict = units_value if isinstance(units_value, dict) else {}
            values = (
                {str(row["field_name"]): row.get("value")}
                if row.get("field_name")
                else {key: row.get(key) for key in ECONOMIC_FIELDS if row.get(key) is not None}
            )
            for field_name, value in values.items():
                if field_name not in ECONOMIC_FIELDS or not isinstance(value, (int, float)):
                    continue
                unit_value = row.get("unit") if row.get("field_name") else units.get(field_name)
                unit = str(unit_value) if unit_value is not None else None
                observations.append(
                    Evidence(
                        source_type=SourceType.USDA_AG_STATISTICS,
                        source=EvidenceSource(
                            publisher=row_source.get("publisher")
                            or source.get(
                                "publisher", "Configured agricultural economics provider"
                            ),
                            dataset=row_source.get("dataset")
                            or source.get("dataset", "Regional enterprise budget"),
                            url=row_source.get("url")
                            or source.get("url")
                            or settings.agriculture_economics_url,
                            vintage=row.get("vintage")
                            or row_source.get("vintage")
                            or source.get("vintage"),
                        ),
                        field_name=field_name,
                        value=float(value),
                        unit=unit,
                        temporal_resolution=row.get("temporal_resolution"),
                        semantic_scope=row.get("geography")
                        or source.get("geography")
                        or "regional planning assumption",
                        confidence=float(row.get("confidence", 0.65)),
                        limitations=row.get("limitations") or source.get("limitations") or [],
                        raw_reference={"activity": activity, "provider_record_id": row.get("id")},
                    )
                )
        return ToolResult(
            tool_name="agriculture.get_economics",
            success=bool(observations),
            observations=observations,
            limitations=[]
            if observations
            else ["Agricultural economics provider returned no usable sourced assumptions."],
        )
