# Implementation status

All phases in the implementation plan have a working code path and automated acceptance coverage where the dependency can run offline.

| Phase | Delivered |
|---|---|
| 0 — Infrastructure | FastAPI and Next.js monorepo, Docker/PostGIS initialization, environment contract, CI, linting, tests, and health checks |
| 1 — Ingestion | Address, listing URL, and natural-language inputs normalize to the same property/investigation contract with claim extraction |
| 2 — World model | Durable investigation/profile snapshots, claims, transition history, evidence provenance, relationships, agent/tool trace, and migration schema |
| 3 — Mireye MCP | MCP initialization and discovery, context, quote and batch support, field normalization, geometry/scope guards, and raw provider references |
| 4 — Agricultural data | EPSG:5070 CropScape CDL history, WGS84 SSURGO lookup, crop/land-use/soil enrichment, and proxy limitations |
| 5 — Autonomous loop | Agent-selected investigations, deterministic VOI ranking, state re-analysis, tool/request/time limits, and decision-stability stopping |
| 6 — Contradiction + VOI | Resolution/semantic compatibility checks, materiality, validated claim transitions, unknown registry, and next-action planning |
| 7 — Market + valuation | Configured benchmark and comparable adapters, traceable weighted indication, uncertainty widening, buyer fit, and stability stress test |
| 8 — Critic + strategy | Property/agriculture/market specialists, critic-requested follow-up, final synthesis, diligence, negotiation, and agent artifacts |
| 9 — Product UI | Run/history/profile flows, live timeline, map, evidence ledger, claims/transitions, valuation/comparables, strategy, and dossier |
| 10 — Evaluation | 20 offline golden cases, metrics report, failure report, connector/unit/API/end-to-end acceptance tests |
| 11 — Hardening | Safe failure behavior, optional bearer auth, CORS, rate limiting, request IDs/security headers, structured logs, retries, caching, and deployment configuration |

External acceptance is configuration-dependent: a real Mireye property context, OpenAI specialist calls, market feeds, and a full Docker startup cannot be certified without provider credentials and a running Docker daemon. The application represents those dependencies explicitly and never fabricates substitute facts.
