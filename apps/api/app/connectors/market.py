from app.config import get_settings
from app.connectors.http import async_client
from app.domain.models import Evidence, EvidenceSource, SourceType, ToolResult


class MarketAdapter:
    async def get_benchmark(self, state: str | None, county: str | None) -> ToolResult:
        url = get_settings().market_benchmark_url
        if not url:
            return ToolResult(
                tool_name="market.get_benchmark",
                success=False,
                limitations=[
                    "MARKET_BENCHMARK_URL is not configured; no market value was inferred."
                ],
            )
        try:
            async with async_client(timeout=45) as client:
                response = await client.get(url, params={"state": state, "county": county})
                response.raise_for_status()
                data = response.json()
            source = data.get("source", {})
            evidence = Evidence(
                source_type=SourceType.MARKET_DATA,
                source=EvidenceSource(
                    publisher=source.get("publisher", "Configured market provider"),
                    dataset=source.get("dataset", "Agricultural land benchmark"),
                    url=source.get("url", url),
                    vintage=source.get("vintage"),
                ),
                field_name="value_per_acre",
                value=data["value_per_acre"],
                unit=data.get("unit", "USD/acre"),
                temporal_resolution=data.get("temporal_resolution"),
                semantic_scope=data.get("semantic_scope", "regional benchmark"),
                confidence=float(data.get("confidence", 0.6)),
                limitations=data.get("limitations", []),
                raw_reference=data.get("raw_reference", {}),
            )
            return ToolResult(
                tool_name="market.get_benchmark", success=True, observations=[evidence]
            )
        except Exception as exc:
            return ToolResult(
                tool_name="market.get_benchmark",
                success=False,
                limitations=[f"Market benchmark unavailable: {type(exc).__name__}"],
            )

    async def find_comparables(
        self, state: str | None, county: str | None, acreage: float | None
    ) -> ToolResult:
        url = get_settings().market_comparables_url
        if not url:
            return ToolResult(
                tool_name="market.find_comparables",
                success=False,
                limitations=[
                    "MARKET_COMPARABLES_URL is not configured; no comparable sale was inferred."
                ],
            )
        try:
            async with async_client(timeout=45) as client:
                response = await client.get(
                    url, params={"state": state, "county": county, "acreage": acreage}
                )
                response.raise_for_status()
                data = response.json()
            source = data.get("source", {})
            observations: list[Evidence] = []
            for comparable in data.get("comparables", []):
                sale_price = float(comparable["sale_price"])
                comparable_acres = float(comparable["acreage"])
                per_acre = sale_price / comparable_acres
                observations.append(
                    Evidence(
                        source_type=SourceType.MARKET_DATA,
                        source=EvidenceSource(
                            publisher=source.get("publisher", "Configured market provider"),
                            dataset=source.get("dataset", "Comparable agricultural sales"),
                            url=comparable.get("source_url") or source.get("url", url),
                            vintage=comparable.get("sale_date") or source.get("vintage"),
                        ),
                        field_name="comparable_value_per_acre",
                        value=per_acre,
                        unit="USD/acre",
                        semantic_scope="comparable agricultural transaction",
                        confidence=float(comparable.get("confidence", 0.65)),
                        limitations=comparable.get("limitations", []),
                        raw_reference={"comparable": comparable},
                    )
                )
            return ToolResult(
                tool_name="market.find_comparables",
                success=bool(observations),
                observations=observations,
                limitations=[]
                if observations
                else ["Comparable provider returned no usable sales."],
            )
        except Exception as exc:
            return ToolResult(
                tool_name="market.find_comparables",
                success=False,
                limitations=[f"Comparable search unavailable: {type(exc).__name__}"],
            )
