from app.config import get_settings
from app.connectors.http import async_client
from app.domain.models import Evidence, EvidenceSource, SourceType, ToolResult

NASS_LAND_VALUE_SERIES = (
    "AG LAND, INCL BUILDINGS - ASSET VALUE, MEASURED IN $ / ACRE"
)


def _nass_number(value: object) -> float | None:
    if not isinstance(value, (str, int, float)):
        return None
    try:
        return float(str(value).replace(",", "").strip())
    except ValueError:
        return None


def select_latest_nass_land_value(rows: object) -> tuple[dict, float] | None:
    if not isinstance(rows, list):
        return None
    candidates: list[tuple[int, dict, float]] = []
    for row in rows:
        if not isinstance(row, dict) or row.get("short_desc") != NASS_LAND_VALUE_SERIES:
            continue
        value = _nass_number(row.get("Value"))
        try:
            year = int(row.get("year", 0))
        except (TypeError, ValueError):
            year = 0
        if value is not None and value > 0:
            candidates.append((year, row, value))
    if not candidates:
        return None
    _, row, value = max(candidates, key=lambda item: item[0])
    return row, value


class MarketAdapter:
    async def get_benchmark(self, state: str | None, county: str | None) -> ToolResult:
        settings = get_settings()
        url = settings.market_benchmark_url
        if not url and not settings.nass_quickstats_api_key:
            return ToolResult(
                tool_name="market.get_benchmark",
                success=False,
                limitations=[
                    (
                        "Neither MARKET_BENCHMARK_URL nor NASS_QUICKSTATS_API_KEY is "
                        "configured; no market value was inferred."
                    )
                ],
            )
        try:
            if not url:
                return await self._get_nass_benchmark(state, county)
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

    async def _get_nass_benchmark(
        self, state: str | None, county: str | None
    ) -> ToolResult:
        settings = get_settings()
        if not state or not settings.nass_quickstats_api_key:
            return ToolResult(
                tool_name="market.get_benchmark",
                success=False,
                limitations=["USDA NASS benchmark requires a resolved state and API key."],
            )
        location_param = (
            {"state_alpha": state.upper()}
            if len(state.strip()) == 2
            else {"state_name": state.upper()}
        )
        params = {
            "key": settings.nass_quickstats_api_key,
            "source_desc": "SURVEY",
            "commodity_desc": "AG LAND",
            "statisticcat_desc": "ASSET VALUE",
            "short_desc": NASS_LAND_VALUE_SERIES,
            "agg_level_desc": "STATE",
            "domain_desc": "TOTAL",
            "freq_desc": "ANNUAL",
            "reference_period_desc": "YEAR",
            "format": "JSON",
            **location_param,
        }
        async with async_client(timeout=45) as client:
            response = await client.get(settings.nass_quickstats_base_url, params=params)
            response.raise_for_status()
            payload = response.json()
        selected = select_latest_nass_land_value(
            payload.get("data") if isinstance(payload, dict) else None
        )
        if not selected:
            return ToolResult(
                tool_name="market.get_benchmark",
                success=False,
                limitations=[f"USDA NASS returned no usable land-value series for {state}."],
            )
        row, value = selected
        year = str(row.get("year", "unknown"))
        limitations = [
            "USDA NASS is a state-level average, not a county benchmark or property appraisal.",
            "The series includes farm buildings and may not match the subject property's land mix.",
        ]
        if county:
            limitations.append(f"The value is not specific to {county}.")
        evidence = Evidence(
            source_type=SourceType.USDA_AG_STATISTICS,
            source=EvidenceSource(
                publisher="USDA National Agricultural Statistics Service",
                dataset="Quick Stats — Farm Real Estate Value",
                url=settings.nass_quickstats_base_url,
                vintage=year,
            ),
            field_name="value_per_acre",
            value=value,
            unit="USD/acre",
            temporal_resolution=f"{year} annual",
            semantic_scope=f"{state} state farm real estate benchmark",
            confidence=0.7,
            limitations=limitations,
            raw_reference={
                "short_desc": row.get("short_desc"),
                "year": row.get("year"),
                "state_name": row.get("state_name"),
                "state_alpha": row.get("state_alpha"),
                "agg_level_desc": row.get("agg_level_desc"),
                "domain_desc": row.get("domain_desc"),
                "unit_desc": row.get("unit_desc"),
                "CV (%)": row.get("CV (%)"),
            },
        )
        return ToolResult(
            tool_name="market.get_benchmark",
            success=True,
            observations=[evidence],
            raw_metadata={"provider": "USDA NASS Quick Stats", "year": year},
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
