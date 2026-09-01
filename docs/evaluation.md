# Evaluation

Run `make eval` to execute the 20 offline golden decision/valuation cases and write `evaluation/reports/latest.json` plus `evaluation/reports/failures.json`. The harness reports decision accuracy, property resolution, valuation bounding, provenance completeness, false-certainty, contradiction recall, unsupported claims, and investigation efficiency. These are controlled offline acceptance metrics; provider-contract acceptance still requires configured credentials and network access. Missing access is reported as a limitation, never replaced with fixtures presented as live evidence.

Golden cases cover supported claims, tillable-acre divergence, flood and drainage issues, irrigation uncertainty, crop continuity, land-use drift, overpricing, attractive pricing, invalid inputs, unavailable providers, incompatible resolution, preference-sensitive materiality, unbounded valuation, and critic-driven thesis reversal.

V2 adds 20 action-level fixtures in `evaluation/cases/v2_agent.json`: five straightforward acquisitions, four claim contradictions, three water/infrastructure uncertainty cases, three crop-versus-livestock cases, two expensive-but-better alternatives, two high-hazard properties, and one insufficient-evidence case. These fixtures assert observable actions, material uncertainties, and acceptable verdict sets rather than a hidden reasoning trace.

The live investigation metrics endpoint (`GET /api/investigations/:id/metrics`) reports tool calls, unavailable calls, material contradictions, alternative-search triggering, termination coverage, recommendation evidence coverage, and Decision-Relevant Evidence Ratio. The ratio counts evidence referenced by a derived signal, contradiction, or valuation against all retrieved evidence.
