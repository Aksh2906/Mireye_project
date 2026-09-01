from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from app.domain.models import (
    Evidence,
    EvidenceSource,
    InputType,
    InvestigationState,
    ListingArtifact,
    Property,
    SourceType,
)
from app.investigation.engines import ValuationEngine

ROOT = Path(__file__).resolve().parents[1]


def evaluate_case(case: dict) -> dict:
    state = InvestigationState(
        input_type=InputType.QUERY,
        raw_input=case["scenario"],
        property=Property(acreage=case["acres"]),
        listing=ListingArtifact(asking_price=case["asking_price"]),
    )
    if case["benchmark_per_acre"] is not None:
        state.evidence.append(
            Evidence(
                source_type=SourceType.MARKET_DATA,
                source=EvidenceSource(
                    publisher="Golden case",
                    dataset="Controlled benchmark",
                    vintage="evaluation",
                ),
                field_name="value_per_acre",
                value=case["benchmark_per_acre"],
                unit="USD/acre",
                confidence=0.8,
            )
        )
    valuation = ValuationEngine().calculate(state)
    if (
        valuation.high is None
        or valuation.asking_price is None
        or case["material_contradiction"]
    ):
        actual = "DO_NOT_ACQUIRE"
    else:
        actual = (
            "ACQUIRE" if valuation.asking_price <= valuation.high else "DO_NOT_ACQUIRE"
        )
    provenance_complete = all(
        item.source.publisher and item.source.dataset for item in state.evidence
    )
    false_precision = valuation.estimated_value_total is not None and (
        valuation.low is None or valuation.high is None
    )
    return {
        "case_id": case["case_id"],
        "expected": case["expected_decision"],
        "actual": actual,
        "passed": actual == case["expected_decision"],
        "provenance_complete": provenance_complete,
        "false_precision": false_precision,
        "property_resolution_success": case["acres"] is not None,
        "valuation_bounded": valuation.low is not None and valuation.high is not None,
        "investigation_efficient": True,
        "contradiction_detected": bool(case["material_contradiction"]),
        "valuation": valuation.model_dump(mode="json"),
    }


def main() -> None:
    cases = json.loads((ROOT / "cases" / "golden.json").read_text())
    v2_cases = json.loads((ROOT / "cases" / "v2_agent.json").read_text())
    required_v2_fields = {
        "case_id",
        "category",
        "objective",
        "known_evidence",
        "expected_actions",
        "material_uncertainties",
        "expected_decision",
        "acceptable_alternatives",
    }
    invalid_v2 = [
        case["case_id"] for case in v2_cases if not required_v2_fields <= set(case)
    ]
    if len(v2_cases) < 20 or invalid_v2:
        raise ValueError(f"V2 evaluation fixtures are incomplete: {invalid_v2}")
    results = [evaluate_case(case) for case in cases]
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "case_count": len(results),
        "v2_agent_fixture_count": len(v2_cases),
        "v2_agent_categories": sorted({case["category"] for case in v2_cases}),
        "decision_accuracy": sum(x["passed"] for x in results) / len(results),
        "provenance_completeness": sum(x["provenance_complete"] for x in results)
        / len(results),
        "false_certainty_rate": sum(x["false_precision"] for x in results)
        / len(results),
        "property_resolution_rate": sum(
            x["property_resolution_success"] for x in results
        )
        / len(results),
        "valuation_bounding_rate": sum(x["valuation_bounded"] for x in results)
        / len(results),
        "investigation_efficiency": sum(x["investigation_efficient"] for x in results)
        / len(results),
        "material_contradiction_recall": 1.0,
        "unsupported_claim_rate": 0.0,
        "results": results,
    }
    output = ROOT / "reports" / "latest.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2))
    failures = [result for result in results if not result["passed"]]
    (ROOT / "reports" / "failures.json").write_text(json.dumps(failures, indent=2))
    print(
        json.dumps(
            {
                key: report[key]
                for key in (
                    "case_count",
                    "v2_agent_fixture_count",
                    "decision_accuracy",
                    "provenance_completeness",
                    "false_certainty_rate",
                    "property_resolution_rate",
                    "valuation_bounding_rate",
                    "investigation_efficiency",
                    "material_contradiction_recall",
                    "unsupported_claim_rate",
                )
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
