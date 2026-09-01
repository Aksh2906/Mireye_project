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

## Agriculture Intelligence V2

| V2 phase | Delivered path |
|---|---|
| Objective | Validated structured `BuyerObjective`, natural-language extraction, crop/livestock/dairy/grazing intent, risk and budget inputs, coordinate mode, and in-investigation objective updates |
| Agent loop | Explicit hypotheses, candidate/executed actions, action VoI events, iteration and cost state, targeted Mireye field requests, stopping reason, and five-way verdict schema |
| Agriculture | Crop registry, crop-history support, activity comparison, crop/grazing/intensity/infrastructure signals, and extension-safe activity models |
| Economics | Conservative/base/optimistic deterministic scenarios, total investment, ROI, payback, break-even yield, dated/geographic assumptions, and refusal to calculate when required inputs are absent |
| Hazards | Dynamic evidence detection and activity-specific agricultural consequence/materiality records; missing observations never imply absence |
| Geometry/map | Polygon/MultiPolygon validation, ring normalization, geodesic acreage, claim divergence, evidence overlays, and human-readable map popups |
| Listings/alternatives | Provider protocol, generic URL and mock adapters, permission-safe LandWatch/Land.com placeholders, explicit unavailable discovery response, and persisted alternative schema |
| UX/reporting | Objective summary, hypothesis panel, agriculture cards, scenarios, hazards, evidence trace, map popups, buyer-context update, and expanded dossier |
| Evaluation | V1 regression suite plus 20 V2 observable-behavior fixtures, V2 engine/API tests, and investigation behavior metrics including Decision-Relevant Evidence Ratio |

Provider-dependent deep alternative search, authoritative parcel retrieval, live hazard feeds, and property-specific crop/livestock economics activate only when their real adapters and sourced data are configured. Their contracts and unavailable behavior are implemented; synthetic live results are intentionally not.

## Decision Intelligence V3

| V3 capability | Delivered path |
|---|---|
| Boundary and map | Persisted boundary provenance, listing/parcel/user priority, GeoJSON validation, claimed-acreage divergence, fit-to-boundary map, layer toggles, hazard/context overlays, and nearby markers |
| Readable evidence | Shared evidence cards, labeled structured facts, source/freshness/confidence/limitations, linked geometry, and raw provider payloads confined to optional technical details |
| Crops and other uses | Risk/evidence-aware crop ordering plus row crop, hay, grazing, cattle, dairy, sheep, goat, orchard, greenhouse, and mixed-use requirement records |
| Investment economics | Editable financing/capex/working-capital inputs, multi-year cash flow, operating ROI, cash-on-cash, NPV, IRR, DSCR, payback/break-even values, and maximum defensible offer |
| Acquisition policy | Deterministic buy, negotiate, investigate, pass, or insufficient-evidence decision integrated into final synthesis |
| Disaster intelligence | Configured hazard adapter, source/vintage/geometry preservation, activity consequences, mitigation actions, explicit scenario stresses, and safe unavailable behavior |
| Listings and alternatives | Configured authorized JSON feed, adaptive radius search, canonical-URL deduplication, screening, top-candidate deep agricultural analysis, map view, and subject-relative advantages/unknowns |
| Product UI | Dedicated map, uses, economics, hazards, alternatives, evidence, and dossier surfaces with direct rerun actions |
| Persistence and tests | V3 PostGIS migration, JSON world-model compatibility, deterministic engine/API fixtures, and provider-unavailable coverage |

Live listing, parcel, hazard, Mireye, crop-economics, and market outputs remain dependent on authorized provider access and source data. The completed implementation reports those configuration gaps explicitly.
