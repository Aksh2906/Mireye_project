# Evaluation

Run `make eval` to execute the 20 offline golden decision/valuation cases and write `evaluation/reports/latest.json` plus `evaluation/reports/failures.json`. The harness reports decision accuracy, property resolution, valuation bounding, provenance completeness, false-certainty, contradiction recall, unsupported claims, and investigation efficiency. These are controlled offline acceptance metrics; provider-contract acceptance still requires configured credentials and network access. Missing access is reported as a limitation, never replaced with fixtures presented as live evidence.

Golden cases cover supported claims, tillable-acre divergence, flood and drainage issues, irrigation uncertainty, crop continuity, land-use drift, overpricing, attractive pricing, invalid inputs, unavailable providers, incompatible resolution, preference-sensitive materiality, unbounded valuation, and critic-driven thesis reversal.
