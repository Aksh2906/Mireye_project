# Mireye Agriculture Decision Intelligence — Expansion Implementation Plan

## 1. Purpose

This plan expands the current Agriculture Intelligence V2 implementation from a property-acquisition investigation into a broader agricultural decision platform.

The requested outcomes are:

1. Recommend better nearby properties or locations.
2. Run comparable analysis on those nearby candidates.
3. Recommend the most economically attractive supported crop.
4. Compare farming with dairy, grazing, livestock, orchard, greenhouse, hay, and mixed-use opportunities where evidence permits.
5. Explain whether a property appears attractive to buy, negotiate, investigate further, or pass on.
6. Resolve and display the farm boundary without presenting an approximation as a legal boundary.
7. Provide activity-specific disaster and hazard analysis.
8. Integrate permitted listing-platform discovery.
9. Present all evidence in a readable, decision-oriented format.

This is an implementation plan only. No work in this document should begin until the user approves the plan.

## 2. Product principles

- A nearby recommendation must be better for the buyer's objective, not merely closer.
- Crop ranking must use risk-adjusted economics and evidence quality, not revenue alone.
- The same analysis pipeline must evaluate the submitted property and every shortlisted alternative.
- A missing hazard observation is `unknown`, not evidence that a hazard is absent.
- A generated or approximate polygon must never be described as a legal parcel boundary.
- Listing claims remain seller claims until corroborated by independent evidence.
- ROI must expose assumptions, source dates, geography, confidence, and sensitivity.
- The system must return `insufficient evidence` rather than fabricate yields, costs, prices, boundaries, listings, or hazards.
- Raw provider payloads may remain available in an optional technical disclosure, but the default interface must be human-readable.
- Provider usage must follow its API/feed terms; the application will not bypass access controls or scrape prohibited sites.

## 3. Current foundation and gaps

### Already implemented

- Buyer objective, budget, acreage, risk tolerance, return target, and activity intent models.
- Crop and agricultural-activity opportunity records.
- Conservative, base, and optimistic economic scenario records.
- ROI, payback, break-even yield, break-even price, and break-even acquisition calculations when sourced inputs exist.
- Activity-specific hazard assessment records.
- Nearby-alternative records and an adaptive radius engine contract.
- Generic listing URL ingestion and provider interfaces.
- Polygon/MultiPolygon validation and geodesic acreage calculation.
- Leaflet evidence geometry rendering with satellite and street base layers.
- Human-readable evidence cards with expandable technical details.
- Claim/evidence graph, provenance, uncertainty, Value of Information, and agent investigation loop.

### Gaps to close

- Listing search currently returns `unavailable` because no permitted live provider is configured.
- LandWatch and Land.com adapters are placeholders rather than live integrations.
- Nearby alternatives are not automatically sent through the full investigation pipeline.
- Crop economics usually cannot run because property-specific yield, price, and cost evidence is incomplete.
- Activity comparison is currently broad and does not yet model dairy/livestock infrastructure and operating economics deeply.
- Hazard analysis only interprets evidence already present; dedicated hazard connectors are missing.
- Boundary validation exists, but authoritative parcel lookup and boundary provenance are not connected end-to-end.
- The map does not distinguish property, parcel, hazard, crop-history, soil, and alternative layers.
- ROI is primarily one-period operating ROI; acquisition decisions need financing, taxes, capex, working capital, and multi-year cash flow.
- Evidence presentation is improved on the evidence and overview pages but needs a shared display-schema registry across all product surfaces.

## 4. Target user journey

1. User submits a listing, address, coordinates, or farming goal.
2. User supplies or confirms acquisition budget, total investment budget, time horizon, financing assumptions, risk tolerance, and preferred activities.
3. System resolves the subject property, evidence scope, and best available boundary.
4. Agent forms hypotheses and requests only decision-relevant evidence.
5. System evaluates crop, dairy, grazing, livestock, orchard, greenhouse, hay, and mixed-use possibilities where the minimum evidence contract is met.
6. System models conservative, base, and optimistic economics for supported uses.
7. System performs activity-specific disaster/hazard analysis and applies hazard stresses to economics.
8. If alternatives could change the decision, the agent searches an adaptive nearby region.
9. Candidates receive cheap screening first; only the strongest candidates receive full analysis.
10. System compares the subject property with shortlisted alternatives using the same evidence and economics contracts.
11. User receives a `buy`, `negotiate`, `investigate`, `pass`, or `insufficient evidence` recommendation with assumptions, risks, and next actions.

## 5. Workstreams

### 5.1 Property boundary and map intelligence

#### Boundary resolution priority

1. Exact geometry supplied by the listing feed.
2. Authoritative parcel geometry from a configured parcel provider or public county GIS endpoint.
3. User-uploaded GeoJSON/KML polygon.
4. User-drawn analysis polygon.
5. Clearly labeled analysis area around a point, used only for contextual queries.

#### Backend work

- Add a `BoundaryRecord` containing geometry, source, boundary kind, retrieval date, confidence, legal-status disclaimer, calculated acreage, and claimed-acreage divergence.
- Add parcel-provider and county-GIS adapter interfaces.
- Add GeoJSON/KML upload normalization and geometry validation.
- Store the selected boundary separately from contextual evidence geometry.
- Create a high-materiality contradiction when boundary acreage materially differs from listing acreage.
- Use the resolved polygon, rather than the centroid alone, for crop, soil, hazard, and nearby queries when the provider supports polygons.

#### Map work

- Add distinct layers for subject boundary, analysis geometry, crop history, soil, hazards, nearby listings, and relevant infrastructure.
- Add layer toggles, legend, fullscreen control, fit-to-boundary, and reset-view controls.
- Use source-specific colors and boundary styles; legal/authoritative, user-drawn, and approximate geometry must look different.
- Add readable popovers with source, vintage, confidence, scope, limitation, and a link to the corresponding evidence card.
- Show alternative candidate cards and map markers in a synchronized selection state.

#### Acceptance criteria

- The map draws the best available polygon and fits the viewport to it.
- Every polygon is labeled by boundary type and provenance.
- Approximate analysis geometry is never labeled as a parcel or legal boundary.
- Invalid/self-inconsistent geometries fail safely.
- Acreage divergence appears in claims, evidence, map, and decision risk.

### 5.2 Readable evidence everywhere

#### Backend work

- Add a normalized evidence presentation contract: title, observation, why it matters, source, scope, confidence, vintage, limitations, and typed facts.
- Preserve raw references for audit without using them as the primary display value.
- Add evidence relationships from crop, activity, ROI, hazard, boundary, and alternative outputs back to source records.

#### Frontend work

- Create a display-schema registry for Mireye, listing, boundary, CDL, SSURGO, market, economics, hazard, and parcel records.
- Reuse the evidence-card component in overview, evidence, crop/activity, economics, hazards, alternatives, strategy, and dossier views.
- Replace remaining technical tables or serialized objects with labeled facts, comparison cards, timelines, and assumption tables.
- Keep raw JSON only in an opt-in `Technical details` disclosure.
- Add source links, freshness badges, confidence explanations, and clear `unknown`/`unavailable` states.

#### Acceptance criteria

- No primary product surface shows serialized JSON.
- Every recommendation links to its supporting evidence and material limitations.
- Complex SSURGO, hazard, and ROI data render as human-readable groups.
- Screen-reader labels and keyboard navigation work for cards, disclosures, layers, and comparison controls.

### 5.3 Crop profitability and agricultural-use comparison

#### Evidence contracts

Each crop requires, at minimum:

- physical suitability or explicit unknown state;
- historical/nearby crop context;
- expected yield with geography, vintage, and source;
- commodity price with unit and source date;
- variable and fixed operating costs;
- water and irrigation assumptions;
- initial infrastructure/capex requirements;
- material hazard exposures;
- market/access or perishability constraints where relevant.

Each non-crop activity requires an activity-specific contract. Examples:

- Dairy: forage/feed plan, water, housing, milking/cooling, manure handling, labor, herd assumptions, milk price, animal health, and regulatory diligence.
- Grazing/beef: usable pasture, carrying-capacity evidence, water, fencing, shelter, feed supplementation, stocking assumptions, and drought sensitivity.
- Orchard/perennial: chill/heat suitability, water, establishment years, bearing-year ramp, labor, pest/frost risk, and market access.
- Greenhouse/controlled environment: power, water, structures, capex, labor, crop cycle, market access, and weather resilience.
- Hay/sheep/goat/mixed: activity-specific yield, stocking, price, operating cost, infrastructure, and risk inputs.

#### Engine work

- Replace the fixed crop shortlist with a region-aware candidate registry.
- Add hard feasibility gates before economic ranking.
- Retrieve sourced yield/price/cost evidence; do not calculate profitability when the minimum evidence contract is incomplete.
- Calculate risk-adjusted opportunity results for each supported crop/activity.
- Rank by buyer objective: return, payback, capital requirement, risk, operational complexity, and evidence quality.
- Return `best supported opportunity`, `best lower-risk alternative`, and `not supportable with current evidence` rather than claiming a universally most-profitable crop.
- Add sensitivity drivers and the evidence that would most change each recommendation.

#### Acceptance criteria

- A crop cannot be called profitable without sourced yield, price, and cost inputs.
- Recommendations explain why a physically suitable crop may still be economically unattractive.
- Dairy/livestock results include facility and working-capital implications.
- Rankings change predictably with buyer risk tolerance, budget, payback target, and return target.
- Unsupported activities remain visible as evidence gaps, not negative conclusions.

### 5.4 ROI and buy/not-buy decision intelligence

#### Financial model

Extend the existing scenarios to include:

- purchase price and closing/transaction costs;
- land and building allocation where supplied;
- initial improvements and replacement capex;
- working capital;
- financing amount, interest rate, term, down payment, and debt service;
- property tax and insurance;
- annual revenue, operating expenses, and owner/labor treatment;
- ramp-up years for dairy, orchard, greenhouse, or other non-immediate production;
- residual value and optional land-appreciation scenario, reported separately from operating performance;
- hazard-related yield, downtime, repair, and insurance stresses.

#### Outputs

- Unlevered and levered cash flow.
- Annual operating profit.
- Cash-on-cash return.
- NPV at the user's hurdle rate.
- IRR when mathematically valid.
- Debt-service coverage ratio.
- Payback period.
- Break-even yield, commodity price, and acquisition price.
- Maximum defensible offer under the user's return/payback target.
- Key sensitivities and evidence confidence.

#### Decision policy

The engine proposes one of:

- `buy`: hurdle is met in the base case and downside remains within the stated risk tolerance;
- `negotiate`: agricultural case is viable but the asking price exceeds the defensible range;
- `investigate`: one or more material, resolvable unknowns could change the decision;
- `pass`: sourced economics or hazards materially contradict the buyer's objective;
- `insufficient evidence`: required inputs are unavailable or too weak.

The agent explains the result, but deterministic code performs the calculations and validates the decision conditions.

#### Acceptance criteria

- Every financial number traces to an input or source-backed assumption.
- The UI separates operating returns from assumed land appreciation.
- No single-point ROI is presented without scenario range and confidence.
- Changing financing, capex, yield, price, or purchase price recalculates the recommendation.
- The recommendation provides a maximum defensible offer and explicit next diligence actions when calculable.

### 5.5 Disaster and hazard intelligence

#### Hazard families

- Flood and inundation.
- Drought and water stress.
- Wildfire.
- Extreme heat and freeze/frost.
- Hail, tornado, hurricane, severe wind, and storm exposure where locally material.
- Erosion, slope instability, and landslide where locally material.
- Activity-specific operational risks such as livestock heat stress, feed disruption, facility outage, or crop-stage sensitivity.

#### Backend work

- Add provider adapters that return geometry, probability/frequency where available, severity, vintage, resolution, and limitations.
- Intersect hazard geometry with the property polygon and calculate affected area only when the geometry supports that calculation.
- Translate physical exposure into consequences for each shortlisted activity.
- Add mitigation options, estimated cost ranges when sourced, insurance/diligence questions, and residual risk.
- Stress the economic scenarios using explicit hazard assumptions rather than hiding a hazard penalty in a master score.
- Add hazard retrieval as a candidate investigation action selected by materiality and Value of Information.

#### Acceptance criteria

- Hazards are prioritized by the proposed agricultural activity and geography.
- The UI does not show an irrelevant generic checklist.
- `No data` and `no observed exposure in the queried dataset` remain distinct.
- Hazard overlays show source, vintage, resolution, and property intersection.
- Material hazards affect cash-flow scenarios and the final decision explanation.

### 5.6 Listing platforms and nearby opportunity discovery

#### Provider strategy

- Implement one permitted production listing feed/API first.
- Keep the existing provider interface so additional sources can be added without changing the analysis engine.
- Continue supporting user-supplied listing URLs and reviewed/manual listings.
- Do not activate LandWatch, Land.com, or any other platform through unauthorized scraping.
- Normalize price, acreage, coordinates, address, description, claimed features, geometry, images, source timestamp, and canonical URL.

#### Search and analysis pipeline

1. Start with the buyer's maximum distance or a 10-mile radius.
2. Expand adaptively to 25, 50, and the buyer's configured limit only when candidate quantity or quality is insufficient.
3. Deduplicate cross-listed properties.
4. Apply cheap hard filters: budget, acreage, distance, prohibited constraints, and missing location.
5. Run shallow screening on remaining candidates: price/acre, crop history, coarse soil/hazard context, boundary availability, and evidence completeness.
6. Select a small shortlist using Value of Information and buyer-objective fit.
7. Run the full subject-property analysis pipeline on the top candidates.
8. Calculate an `Alternative Opportunity Delta` explaining advantages, disadvantages, material unknowns, economics, and confidence relative to the submitted property.
9. Return a ranked shortlist, not a raw listing feed.

#### API and orchestration work

- Convert `/api/opportunities/search` from a static unavailable response into a provider-backed asynchronous search.
- Add an investigation-scoped nearby-search action so alternatives persist in the world model and timeline.
- Allow a user to promote an alternative into a new full investigation while preserving comparison links.
- Add provider failure, quota, stale-listing, and deleted-listing states.

#### Acceptance criteria

- Search obeys buyer budget, acreage, activity, risk, and distance constraints.
- Every alternative includes source URL, retrieval time, evidence quality, and investigation depth.
- The system performs deep analysis only on the most decision-relevant candidates.
- Candidate comparison uses identical economics and hazard contracts.
- When no provider is configured, the product explains setup requirements and does not fabricate listings.

## 6. Shared domain and API changes

### New or extended domain records

- `BoundaryRecord`
- `BoundaryProvenance`
- `CropEconomicsProfile`
- `ActivityEconomicsProfile`
- `FinancialInputs`
- `CashFlowYear`
- `InvestmentDecision`
- `HazardObservation`
- `HazardImpactScenario`
- `ListingCandidate`
- `CandidateAnalysisSummary`
- `PropertyComparison`
- `EvidenceDisplayRecord`

### API shape

Prefer investigation-scoped actions so results remain part of the evidence/world model:

- `POST /api/investigations/{id}/actions/resolve-boundary`
- `POST /api/investigations/{id}/actions/evaluate-uses`
- `POST /api/investigations/{id}/actions/analyze-hazards`
- `POST /api/investigations/{id}/actions/model-investment`
- `POST /api/investigations/{id}/actions/search-nearby`
- `POST /api/investigations/{id}/alternatives/{alternative_id}/investigate`
- `POST /api/investigations/{id}/financial-inputs`
- `POST /api/investigations/{id}/boundary`

The existing `POST /api/investigations/{id}/run` remains the autonomous entry point and may select these actions itself. Direct action endpoints let the user explicitly request or rerun a section.

## 7. Frontend information architecture

Add dedicated investigation tabs or sections:

- `Overview`: verdict, best use, best crop, return range, major risk, and nearby alternative summary.
- `Map`: boundary and switchable evidence layers.
- `Uses`: crop, dairy, grazing, livestock, orchard, greenhouse, hay, and mixed-use comparison.
- `Economics`: assumptions, scenarios, cash flows, sensitivity, maximum offer, and buy/negotiate/investigate/pass result.
- `Hazards`: prioritized disaster exposures, agricultural consequences, mitigations, and map layers.
- `Alternatives`: listing search controls, adaptive search progress, shortlist, map, and subject-vs-candidate comparison.
- `Evidence`: readable source cards and optional technical details.
- `Strategy/Dossier`: final recommendation, diligence, negotiation, and next actions.

## 8. Implementation sequence

### Phase 0 — Contracts and fixtures

- Finalize domain models, provider interfaces, database migration, environment contract, and offline fixtures.
- Extend evaluation cases for crop profitability, dairy/grazing, financing, hazard uncertainty, boundaries, and alternatives.
- No live provider dependency in automated tests.

Exit: schemas migrate cleanly and fixtures cover all requested user journeys.

### Phase 1 — Boundary, map, and evidence foundation

- Implement boundary resolution/storage/upload.
- Upgrade map layers and interaction.
- Complete the shared evidence display registry across pages.

Exit: subject property has a provenance-labeled geometry or an explicit `boundary unavailable` state; no primary UI shows raw JSON.

### Phase 2 — Crop, activity, and financial engines

- Build evidence contracts and provider-backed assumption retrieval.
- Implement crop/activity feasibility gates and ranking.
- Implement multi-year, financing-aware ROI and investment decision policy.

Exit: at least one fully sourced crop case, one dairy/grazing case, and one insufficient-evidence case pass deterministic tests.

### Phase 3 — Disaster intelligence

- Add hazard adapters, polygon intersections, activity consequences, map layers, and financial stress scenarios.
- Add agent actions and Value-of-Information rules for hazard retrieval.

Exit: activity-specific hazards change the economics and recommendation only through visible sourced assumptions.

### Phase 4 — Listing provider and nearby discovery

- Connect one approved listing provider.
- Implement adaptive search, deduplication, screening, shortlist selection, deep candidate analysis, and comparison.

Exit: a submitted property can be compared with at least three provider or reviewed-fixture candidates, with the best candidate receiving a full analysis.

### Phase 5 — Decision UX and end-to-end synthesis

- Complete new tabs, comparison views, progress events, final dossier, and direct rerun actions.
- Add maximum-offer and next-diligence guidance.
- Run accessibility, responsive, performance, and browser verification.

Exit: the full user journey produces an evidence-backed subject analysis, supported-use recommendation, hazard-adjusted economics, nearby shortlist, and final acquisition recommendation.

### Indicative delivery effort

For one developer working sequentially:

| Phase | Estimated effort |
|---|---:|
| Phase 0 — Contracts and fixtures | 1–2 development days |
| Phase 1 — Boundary, map, and evidence | 3–5 development days |
| Phase 2 — Crop, activity, and finance | 6–9 development days |
| Phase 3 — Disaster intelligence | 4–6 development days |
| Phase 4 — Listings and nearby discovery | 5–8 development days after provider access |
| Phase 5 — Decision UX and synthesis | 4–6 development days |

Total indicative engineering effort is 23–36 development days, excluding provider procurement, account approval, and delays obtaining authoritative datasets. Phases should be demonstrated and accepted independently rather than held for one large release.

## 9. Testing and evaluation

### Unit tests

- Geometry validation, acreage divergence, and boundary precedence.
- Crop/activity evidence gates and ranking.
- Multi-year cash flow, NPV, IRR, DSCR, payback, and break-even calculations.
- Hazard intersection and scenario stresses.
- Listing normalization, deduplication, radius expansion, and comparison deltas.
- Evidence display-schema transformations.

### Integration tests

- Provider success, timeout, quota, malformed response, stale data, and unavailable states.
- Investigation persistence and reruns.
- Alternative promotion to a full investigation.
- Claims/evidence/decision linkage.

### End-to-end cases

- Profitable crop property with adequate evidence.
- Physically suitable crop that fails economically.
- Dairy opportunity limited by infrastructure budget.
- Grazing property with drought sensitivity.
- Asking price above maximum defensible offer.
- Subject property inferior to a more expensive nearby candidate.
- Boundary acreage contradiction.
- Material flood or wildfire exposure.
- No listing provider configured.
- Missing economic inputs resulting in `insufficient evidence`.

### Quality metrics

- Recommendation evidence coverage.
- Decision-relevant evidence ratio.
- Unsupported-claim rate.
- Alternative screening-to-deep-analysis ratio.
- Data freshness and geography-match rate.
- Calculation reproducibility.
- Provider failure transparency.

## 10. Setup and external decisions required

Before provider-backed production behavior can be completed, the following must be selected or configured:

1. **Listing provider** — an authorized API/feed or reviewed dataset with search rights, coordinates, price, acreage, source URL, and update timestamps.
2. **Parcel/boundary provider** — a national parcel service or a supported set of authoritative county GIS adapters.
3. **Economic inputs** — USDA/NASS access plus a maintained source for regional enterprise budgets or user-supplied budgets.
4. **Hazard sources** — approved flood, drought, wildfire, severe-weather, and climate datasets with appropriate spatial and usage terms.
5. **Financial defaults** — whether the app supplies editable benchmark financing/tax/insurance assumptions or requires the user to enter them.
6. **Activity scope** — recommended first production set: row crops, hay, grazing/beef cattle, and dairy; orchard, greenhouse, sheep, goats, and mixed use can follow behind the same contracts.

Existing configuration remains required for full agent behavior:

- `OPENAI_API_KEY`
- `MIREYE_API_TOKEN` or `MIREYE_MCP_TOKEN`
- `NASS_QUICKSTATS_API_KEY` when using Quick Stats
- Market benchmark/comparable configuration where applicable

Provider-specific environment keys should be added only after the provider choice is approved; the implementation should not invent or hard-code credentials.

## 11. Recommended approval scope

Approve Phases 0–5 as the product direction, with two explicit external gates:

- **Gate A:** choose and authorize one listing provider before Phase 4 live integration.
- **Gate B:** choose a parcel/boundary provider before Phase 1 production parcel lookup.

Development can still proceed with reviewed fixtures and user-uploaded boundaries while those provider decisions are pending. Production results must remain clearly unavailable where a required provider is not configured.
