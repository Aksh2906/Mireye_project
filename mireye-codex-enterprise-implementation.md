# Farm Acquire Implementation Plan
## Codex Enterprise End-to-End Implementation Specification

**Status:** Build specification
**Product:** Agriculture-specific autonomous land acquisition investigation platform
**Primary integration:** Mireye MCP
**Agent runtime:** OpenAI API, agent use only
**Frontend:** Next.js + TypeScript
**Backend:** Python + FastAPI
**Database:** PostgreSQL + PostGIS
**Deployment:** Docker-first, production-ready

---

# 1. Executive Summary

Build a full-stack product that investigates agricultural land acquisitions rather than merely screening parcels.

The user can independently start an investigation with any of:

1. A property address.
2. A listing URL.
3. A natural-language acquisition query containing property information.

The user also provides persistent buyer context such as budget, acreage preference, geography, agricultural objectives, risk tolerance, investment horizon, and desired use.

The system autonomously:

1. Identifies and normalizes the property.
2. Extracts seller/listing claims and buyer objectives.
3. Builds an initial acquisition thesis.
4. Determines what evidence is needed.
5. Uses Mireye MCP and external agricultural/market data tools.
6. Combines sources into derived signals that no single source states.
7. Tracks claims and evidence in a persistent world model.
8. Detects contradictions.
9. Determines whether contradictions are material to the buyer.
10. Estimates the value of obtaining additional information.
11. Chooses additional investigations when they can materially change the decision.
12. Repeats the investigation loop autonomously.
13. Produces a binary acquisition verdict.
14. Produces an evidence-backed financial valuation.
15. Produces risks, uncertainties, diligence requests, negotiation recommendations, and next actions.
16. Saves the investigation and buyer context for future investigations.

The system must behave as an autonomous investigation system, not a chatbot, dashboard, deterministic weighted score, or thin LLM wrapper around Mireye.

---

# 2. Product Principle

The core question is:

> "Given what this buyer wants and what is currently known about this agricultural property, what evidence would most change the acquisition decision, and what does the available evidence currently imply?"

Do NOT implement:

> fetch Mireye -> display fields -> calculate score -> verdict

Implement:

> claims -> evidence -> enrichment -> contradiction -> materiality -> value of information -> next investigation -> updated thesis -> valuation -> acquisition decision -> strategy

The agent must be allowed to change its investigation path based on discoveries.

The project brief explicitly requires the agent to make decisions that are not hardcoded and to fuse Mireye with another US dataset. Carry this principle through every subsystem.

---

# 3. Primary Product Experience

The homepage should present three independent investigation entry modes.

## 3.1 Address mode

Input:

```text
123 County Road, Iowa
```

Optional buyer context:

```text
Looking for low-risk row-crop land under $1.5M.
Prefer irrigated land.
```

The agent geocodes and investigates the property.

## 3.2 Listing URL mode

Input:

```text
https://example.com/listing/123
```

The system retrieves the listing where technically/legal permitted, extracts relevant property information, seller claims, acreage, price, agricultural claims, and other evidence.

The listing content is treated as CLAIM SOURCE, not ground truth.

## 3.3 Natural-language mode

Input:

```text
I'm considering an 85-acre Iowa farm listed for $1.2M.
The seller says 70 acres are tillable and it has excellent drainage.
I care about row-crop productivity and low flood risk.
Is this a good acquisition?
```

The agent extracts:

- property
- asking price
- acreage
- seller claims
- buyer objectives
- constraints
- missing information

Then begins the same investigation graph.

## 3.4 Invalid/underspecified query

If a query contains no identifiable property and is purely a generic agricultural market question, the application should explain that the investigation product requires a property-level acquisition target and ask for an address, listing URL, or property description.

Do not silently turn the product into a generic agricultural research chatbot.

---

# 4. Buyer Profile

Persist buyer context separately from individual investigations.

## Buyer profile fields

```text
id
name
target_states
target_counties
target_regions
minimum_acres
maximum_acres
budget_min
budget_max
preferred_crops
irrigation_preference
risk_tolerance
investment_horizon_years
desired_land_use
desired_return
financing_assumptions
flood_risk_tolerance
soil_preferences
access_preferences
water_preferences
valuation_preferences
created_at
updated_at
```

The profile must be editable.

The investigation agent may reference the profile but must not silently modify it.

When a user explicitly establishes a persistent preference during an investigation, expose it as a "remember preference" action in the UI. Only persist it automatically if product requirements later explicitly allow this.

---

# 5. Investigation Model

Each investigation is a durable entity.

```text
Investigation
├── Property
├── BuyerSnapshot
├── InputArtifacts
├── Claims
├── Evidence
├── DerivedSignals
├── Contradictions
├── Unknowns
├── AgentRuns
├── ToolCalls
├── Valuation
├── Decision
├── DiligencePlan
├── NegotiationStrategy
└── FinalDossier
```

Take a snapshot of the buyer profile at investigation creation time so that historical reports remain reproducible even if the buyer later changes preferences.

---

# 6. Binary Decision

The headline decision must be binary:

```text
ACQUIRE
DO NOT ACQUIRE
```

The decision must always include a qualification:

```text
ACQUIRE
  - Proceed
  - Proceed with conditions

DO NOT ACQUIRE
  - Current price is unjustified
  - Material uncertainty is unresolved
  - Fundamental property mismatch
  - Risk exceeds buyer tolerance
```

Do not output a raw score as the decision.

Example:

> DO NOT ACQUIRE AT CURRENT PRICE

Reason:

> The property appears agriculturally viable, but the asking price assumes approximately 70 tillable acres while independent evidence supports a materially smaller cultivated footprint. The valuation therefore does not justify the current asking price.

The agent may recommend renegotiation as the action even though the headline remains binary.

---

# 7. Input Normalization Pipeline

Create an `InputResolver`.

Responsibilities:

1. Detect input type.
2. Extract property information.
3. Resolve address.
4. Resolve coordinates.
5. Normalize acreage.
6. Normalize asking price.
7. Identify listing source.
8. Extract seller claims.
9. Extract buyer requirements.
10. Identify missing critical information.

Output structured object:

```json
{
  "property": {
    "address": "...",
    "latitude": 0,
    "longitude": 0,
    "state": "...",
    "county": "...",
    "parcel_identifier": null,
    "acreage": null
  },
  "listing": {
    "url": "...",
    "asking_price": null,
    "source": "...",
    "raw_text": "..."
  },
  "claims": [],
  "buyer_objectives": [],
  "uncertainties": []
}
```

Do not fabricate values.

---

# 8. Listing Ingestion

Implement a pluggable listing ingestion tool.

Tools:

```text
listing.fetch
listing.extract_property
listing.extract_claims
listing.extract_price
listing.extract_agricultural_attributes
```

Treat extracted listing information as evidence with source metadata.

Every extracted claim must have:

```text
claim_id
claim_text
claim_type
source_id
source_location
extraction_confidence
created_at
```

Examples:

```text
"70 acres tillable"
"excellent drainage"
"irrigated"
"productive soils"
"no flood issues"
"year-round road access"
```

The agent should proactively identify claims likely to affect valuation.

---

# 9. Evidence Model

Every evidence object must preserve provenance.

```text
Evidence {
  id
  investigation_id
  source_type
  source_name
  source_url
  publisher
  retrieved_at
  vintage
  spatial_resolution
  temporal_resolution
  field_name
  value
  unit
  geometry
  confidence
  limitations
  raw_reference
}
```

Possible source types:

```text
MIREYE
USDA_CDL
USDA_SSURGO
USDA_AG_STATISTICS
MARKET_DATA
LISTING
USER_PROVIDED
GEOCODER
WEB_SOURCE
DERIVED
```

A derived signal must reference the evidence objects used to derive it.

---

# 10. Claim State Machine

Implement the claim state machine from the existing project design.

```text
UNKNOWN
   |
   +--> LOW_CONFIDENCE
   |
   +--> UNDER_INVESTIGATION
   |
   +--> SUPPORTED
   |
   +--> PARTIALLY_SUPPORTED
   |
   +--> CONTRADICTED
   |
   +--> NOT_MATERIAL
```

State transitions must be represented explicitly.

Do not allow an LLM to directly mutate arbitrary claim state.

The LLM proposes a state transition with evidence references.

A deterministic validator validates that:

- referenced evidence exists
- evidence supports the proposed transition
- confidence is within allowed bounds
- the transition is permitted

---

# 11. Claim-Evidence Graph

Represent the investigation as a graph.

Nodes:

```text
CLAIM
EVIDENCE
SIGNAL
CONTRADICTION
UNKNOWN
DECISION
```

Edges:

```text
SUPPORTS
CONTRADICTS
DERIVED_FROM
RELEVANT_TO
DEPENDS_ON
AFFECTS
RESOLVES
```

Example:

```text
Seller Claim:
"70 acres tillable"
        |
        +---- supported by ---> Listing
        |
        +---- contradicted by -> Historical Crop Footprint
                                      |
                                      +-> derived from CDL
                                      |
                                      +-> derived from Mireye land context
```

This graph should power the UI's evidence trace.

---

# 12. Mireye Integration

Use Mireye MCP as the primary physical-world tool layer.

Create a dedicated server-side `MireyeToolAdapter`.

The agent must never receive the raw Mireye API key.

The key lives only in server-side secrets.

The adapter should expose normalized application tools such as:

```text
mireye.get_field_catalog()
mireye.quote_request()
mireye.fetch_context()
mireye.fetch_batch_context()
```

If the MCP server exposes different exact tool names, create a translation layer rather than leaking provider-specific names throughout the application.

## Mireye principles

1. Discover available fields before assuming fields exist.
2. Never invent Mireye fields.
3. Preserve source citations.
4. Preserve field metadata.
5. Track request cost.
6. Cache results where safe.
7. Batch coordinate requests.
8. Store exact requested fields.
9. Store exact returned values.
10. Store retrieval timestamp.

The product must support the hack requirement that evidence remains traceable back to the original fields.

---

# 13. External Agricultural Data

Implement external data adapters behind a common interface.

Required initial datasets:

## USDA Cropland Data Layer

Use for:

- historical crop presence
- cultivated footprint
- crop continuity
- land-use transitions
- agricultural continuity
- land-use drift

Tool interface:

```text
agriculture.get_crop_history(
  geometry,
  years
)
```

## USDA SSURGO / soil context

Use for:

- soil characteristics
- drainage-related soil limitations
- agricultural soil context
- soil uncertainty

Tool:

```text
agriculture.get_soil_context(
  geometry
)
```

## Agricultural market/economic data

Add an adapter for public agricultural land market benchmarks.

The exact source should be configurable.

Do not hardcode a single data vendor into valuation logic.

---

# 14. External Data Adapter Contract

Every dataset adapter must return:

```json
{
  "source": {
    "publisher": "...",
    "dataset": "...",
    "url": "...",
    "retrieved_at": "...",
    "vintage": "..."
  },
  "observations": [],
  "geometry": {},
  "limitations": []
}
```

Never return untraceable numbers.

---

# 15. Enrichment Engine

The enrichment engine creates signals that no individual source explicitly states.

Required derived signals:

## Agricultural Continuity

Measures whether the property has shown persistent agricultural use across historical observations.

Conceptually:

```text
Agricultural Continuity =
agricultural-use observations / valid historical observations
```

Do not use a hardcoded arbitrary threshold without documenting the reason.

## Seller Claim Divergence

Measures the disagreement between a seller claim and independent evidence.

Example:

```text
seller_tillable_acres = 70
independent_cultivated_footprint = 60
divergence = 10 acres
```

Do not call this proof that the seller is wrong.

Call it:

> Independent evidence does not fully corroborate the claim.

## Land Use Drift

Detect meaningful change in observed land use over time.

## Physical-Agricultural Consistency

Compare:

- Mireye terrain
- Mireye land cover
- soil context
- crop history
- seller claims

to determine whether the agricultural narrative is internally coherent.

## Access/Operational Friction

Combine physical access and agricultural operational context.

## Water/Drainage Risk Signal

Combine relevant physical, soil, flood/hazard, and agricultural evidence.

Do not infer legal water rights from these signals.

---

# 16. Enrichment Contract

Every signal must include:

```json
{
  "signal_id": "...",
  "name": "...",
  "value": 0,
  "interpretation": "...",
  "materiality": "LOW|MEDIUM|HIGH",
  "evidence_ids": [],
  "method": "...",
  "limitations": []
}
```

The `method` must be human-readable.

Example:

> Historical agricultural-use observations were compared against listing acreage and independent spatial evidence. The result indicates a discrepancy in cultivated footprint, but does not establish legal tillable acreage.

---

# 17. Multi-Agent Architecture

Use an orchestrator with specialized agents.

## 17.1 Acquisition Orchestrator

Responsibilities:

- own investigation lifecycle
- maintain state
- select specialist agents
- determine whether more evidence is needed
- enforce stopping conditions
- synthesize final decision

It should NOT independently fabricate domain facts.

## 17.2 Property Intelligence Agent

Responsibilities:

- physical property analysis
- terrain
- land cover
- hazards
- access
- utilities
- built environment
- property-use constraints

Primary tools:

```text
mireye.*
geospatial.*
```

## 17.3 Agricultural Intelligence Agent

Responsibilities:

- crop history
- soil context
- agricultural continuity
- land-use drift
- cultivated footprint
- agricultural claims

Primary tools:

```text
agriculture.*
mireye.*
enrichment.*
```

## 17.4 Market & Valuation Agent

Responsibilities:

- identify valuation factors
- gather market evidence
- identify comparables
- normalize comparables
- calculate indicated value
- quantify uncertainty

Primary tools:

```text
market.*
valuation.*
calculator.*
```

## 17.5 Evidence Critic Agent

Responsibilities:

- challenge current thesis
- identify unsupported assumptions
- detect overclaiming
- identify conflicting evidence
- identify evidence-resolution mismatches
- recommend investigations

This agent must explicitly attempt to falsify the current acquisition thesis.

## 17.6 Strategy Agent

Responsibilities:

- interpret final evidence
- produce diligence requests
- produce negotiation strategy
- identify conditions
- generate monitoring recommendations
- explain decision

---

# 18. Agent Communication

Agents must communicate through structured state, not conversational text.

Example:

```json
{
  "investigation_id": "...",
  "current_thesis": "...",
  "critical_claims": [],
  "material_risks": [],
  "unknowns": [],
  "evidence_summary": [],
  "recommended_next_actions": []
}
```

Each agent returns a structured proposal.

The orchestrator validates and commits state changes.

---

# 19. Agent Tools

Implement tools corresponding to the existing project design.

```text
mireye.fetch_context
external.get_crop_history
external.get_soil_context
geospatial.intersect
enrichment.derive_signal
evidence.compare_claim
evidence.calculate_confidence
investigation.calculate_value_of_information
investigation.select_next_action
deal.update_memory
diligence.create_request
negotiation.create_strategy
report.generate_dossier
```

Add:

```text
listing.fetch
listing.extract_claims
market.find_comparables
market.get_benchmark
valuation.calculate
valuation.compare_to_asking_price
world_model.get_state
world_model.commit_update
```

---

# 20. Value of Information

This is a core intelligence mechanism.

The agent should not simply fetch everything.

For each possible investigation:

```text
Investigation candidate
        |
        +--> potential decision impact
        +--> uncertainty reduction
        +--> evidence quality
        +--> cost
        +--> expected usefulness
```

Conceptual:

```text
VOI =
expected decision improvement
× materiality
× uncertainty
× evidence reliability
-
investigation cost
```

The exact implementation must be documented and deterministic once the agent has proposed the factors.

The LLM proposes candidate investigations.

A deterministic calculator evaluates them.

The agent chooses among the validated candidates.

Because the user explicitly allows broad credit usage, do not prematurely stop based purely on Mireye credits. Still track cost and avoid obviously redundant requests.

---

# 21. Investigation Loop

Pseudo-flow:

```python
while not stopping_condition:

    state = world_model.load()

    orchestrator.identify_critical_unknowns()

    candidate_actions = specialist_agents.propose_investigations()

    validated_actions = validate_actions(candidate_actions)

    ranked_actions = calculate_voi(validated_actions)

    next_action = orchestrator.select_action(ranked_actions)

    result = execute_tool(next_action)

    evidence = normalize_result(result)

    world_model.commit(evidence)

    signals = derive_signals(state, evidence)

    claims = update_claim_states(state, evidence, signals)

    contradictions = detect_contradictions(state)

    materiality = assess_materiality(
        contradictions,
        buyer_context,
        valuation_context
    )

    thesis = update_thesis(...)

    critic_result = evidence_critic.review(...)

    if critic_result.requires_investigation:
        continue

    if decision_stability_is_high(...):
        break
```

Never use a fixed number of agent loops as the only stopping condition.

---

# 22. Stopping Criteria

The orchestrator should stop when:

1. Critical claims are sufficiently resolved.
2. No unresolved high-materiality contradiction remains.
3. Additional investigations have low expected decision impact.
4. Acquisition verdict is stable under plausible uncertainty.
5. Valuation range is sufficiently bounded.
6. Buyer-specific requirements have been addressed.

Also enforce safety limits:

```text
max wall-clock time
max total agent turns
max tool calls
max duplicate calls
max external requests
```

These are circuit breakers, not reasoning rules.

---

# 23. Contradiction Engine

The system must distinguish:

```text
difference
vs
contradiction
```

A difference in spatial resolution is not automatically a contradiction.

For example:

```text
Listing:
70 tillable acres

CDL:
60 acres cultivated footprint
```

Correct interpretation:

> Independent historical spatial evidence supports approximately 60 acres of observed cultivation and does not independently corroborate the 70-acre tillable claim.

Incorrect:

> Seller lied about acreage.

The contradiction engine must consider:

- dataset resolution
- vintage
- temporal mismatch
- geometry mismatch
- semantic mismatch
- measurement uncertainty

---

# 24. Materiality Engine

A contradiction becomes material only if it can affect the acquisition decision.

Example:

```text
10 sq ft driveway discrepancy
```

probably not material.

```text
10-acre tillable discrepancy
```

could materially affect valuation.

Materiality must incorporate buyer context.

For example, a flood issue may be:

```text
HIGH materiality
```

for a buyer with strict flood-risk tolerance but lower for a speculative buyer.

The agent must explain materiality.

---

# 25. Financial Valuation Architecture

Do NOT use a single opaque LLM-generated price.

Create a valuation subsystem.

## Inputs

```text
asking_price
total_acres
estimated_tillable_acres
agricultural_use
crop_history
soil_context
water/irrigation indicators
drainage indicators
flood/hazard exposure
access
location
market benchmarks
comparables
buyer requirements
```

## Output

```json
{
  "estimated_value_total": 0,
  "estimated_value_per_acre": 0,
  "low": 0,
  "high": 0,
  "asking_price": 0,
  "price_gap": 0,
  "confidence": 0,
  "key_value_drivers": [],
  "key_downside_drivers": [],
  "assumptions": [],
  "evidence_ids": []
}
```

Use a range, not false precision.

---

# 26. Valuation Method

Use multiple evidence modes where available:

### Market benchmark

Regional/public agricultural land value information.

### Comparable properties

Normalize for:

- acreage
- agricultural use
- tillable acreage
- irrigation
- location
- access
- land characteristics

### Property-specific adjustments

Only where the relationship is supported.

The agent should produce:

```text
Base market indication
+
supported positive factors
-
supported negative factors
=
indicated value range
```

Every adjustment needs a reason and evidence.

If evidence is insufficient, widen the range instead of inventing an adjustment.

---

# 27. Decision Logic

The final decision is agentic, but numerical constraints should be deterministic.

The agent evaluates:

```text
buyer fit
+
physical reality
+
agricultural reality
+
economic reality
+
risk
+
uncertainty
```

Decision output:

```json
{
  "verdict": "ACQUIRE|DO_NOT_ACQUIRE",
  "confidence": 0,
  "decision_summary": "...",
  "critical_reasons": [],
  "conditions": [],
  "valuation": {},
  "unresolved_uncertainties": []
}
```

The confidence must describe confidence in the evidence-backed conclusion, not statistical certainty about the property.

---

# 28. Strategy Output

The final strategy should contain:

## Due diligence

Prioritized:

```text
P0 - must verify before closing
P1 - should verify
P2 - useful but non-critical
```

Examples:

- tillable acreage documentation
- drainage records
- irrigation documentation
- historical yield records
- access/easement documentation
- flood history
- soil verification

Do not claim legal rights based on physical datasets.

## Negotiation

Examples:

```text
price contingency
acreage contingency
drainage verification contingency
irrigation verification
seller documentation request
```

The strategy should connect each recommendation to evidence.

---

# 29. Final Dossier

The final result page should contain:

## Header

```text
PROPERTY
ADDRESS

ACQUISITION VERDICT
ACQUIRE / DO NOT ACQUIRE

Confidence: XX%
```

## Executive thesis

A concise explanation.

## Property reality

- acreage
- land-use context
- physical characteristics
- access
- hazards

## Seller claims

Table:

| Claim | Evidence | Status | Materiality |
|---|---|---|---|

## Agricultural analysis

- crop history
- cultivated footprint
- soil context
- agricultural continuity
- land-use drift

## Contradictions

Each contradiction:

```text
Claim
Independent evidence
Why it differs
Materiality
Impact
```

## Valuation

```text
Asking price
Estimated fair value range
Price/acre
Value/acre
Gap
```

## Decision reasoning

Explicit causal chain.

## Risks

Ranked.

## Unknowns

Ranked.

## Due diligence

Prioritized.

## Negotiation strategy

Actionable.

## Evidence

Every important conclusion linked to source evidence.

---

# 30. UI Architecture

Use Next.js App Router.

Pages:

```text
/
  landing + new investigation

/investigate
  input selection

/investigate/address
/investigate/listing
/investigate/query

/investigation/[id]
  live investigation

/investigation/[id]/evidence
/investigation/[id]/claims
/investigation/[id]/valuation
/investigation/[id]/strategy

/profile
  buyer preferences

/history
  previous investigations
```

---

# 31. Live Investigation UX

Do not show a generic chatbot interface.

Show an investigation timeline:

```text
✓ Property identified
✓ Seller claims extracted
✓ Physical context investigated
✓ Agricultural history investigated
⚠ Tillable acreage discrepancy found
✓ Materiality assessed
↻ Investigating market implications
↻ Re-evaluating valuation
...
✓ Decision reached
```

Allow users to expand each stage and see evidence.

The agent should stream high-level events, not hidden chain-of-thought.

Never expose private chain-of-thought.

Instead show:

```text
"Investigating drainage because it materially affects the seller's productivity claim."
```

---

# 32. Evidence UI

Each evidence item should show:

```text
Source
Publisher
Dataset
Date/vintage
Field
Value
Unit
Spatial scope
Limitations
```

Mireye citations should be clickable where possible.

---

# 33. Map UI

Use MapLibre or another appropriate map library.

Display:

- property location
- investigation geometry
- relevant spatial evidence
- crop-history context
- hazard context where available

Do not imply parcel boundaries if the system has not obtained a reliable parcel boundary.

---

# 34. Backend Architecture

FastAPI services:

```text
api/
├── investigations
├── properties
├── buyer_profiles
├── evidence
├── claims
├── valuation
├── reports
└── health
```

Internal services:

```text
agents/
tools/
world_model/
enrichment/
valuation/
investigation/
provenance/
connectors/
```

Keep provider integrations separate from domain logic.

---

# 35. Suggested Repository

```text
mireye-agri-agent/
├── apps/
│   ├── web/
│   │   ├── app/
│   │   ├── components/
│   │   ├── lib/
│   │   └── hooks/
│   └── api/
│       ├── app/
│       │   ├── api/
│       │   ├── agents/
│       │   ├── tools/
│       │   ├── world_model/
│       │   ├── enrichment/
│       │   ├── valuation/
│       │   ├── investigation/
│       │   ├── connectors/
│       │   └── provenance/
│       └── tests/
├── packages/
│   ├── schemas/
│   ├── agent-contracts/
│   └── shared/
├── infrastructure/
│   ├── docker/
│   └── migrations/
├── evaluation/
│   ├── cases/
│   ├── runners/
│   └── reports/
├── docs/
└── docker-compose.yml
```

---

# 36. Database

Use PostgreSQL + PostGIS.

Core tables:

```text
users
buyer_profiles
buyer_profile_preferences

properties
investigations
investigation_inputs
investigation_runs

claims
claim_state_transitions

evidence
evidence_sources
evidence_relationships

derived_signals
contradictions
unknowns

agent_runs
agent_actions
tool_calls

valuations
valuation_factors
comparables

decisions
diligence_requests
negotiation_strategies

reports
```

Use UUID primary keys.

Use JSONB for provider-specific metadata.

Use relational fields for important queryable properties.

---

# 37. Agent Run Persistence

Persist:

```text
agent_name
run_id
investigation_id
started_at
completed_at
status
input_state_hash
output_summary
tool_calls
errors
```

Do not persist raw chain-of-thought.

Persist concise reasoning artifacts:

```text
decision rationale
evidence references
selected action
reason for action
```

---

# 38. OpenAI Integration

Use OpenAI exclusively for agent functionality.

Do not use the OpenAI key for:

- generic frontend text generation
- UI copy
- unrelated summarization endpoints
- non-agent application logic

Create an isolated agent runtime.

Suggested conceptual architecture:

```text
FastAPI
  |
  v
Agent Runtime
  |
  +-- Orchestrator
  +-- Property Agent
  +-- Agriculture Agent
  +-- Market Agent
  +-- Critic Agent
  +-- Strategy Agent
  |
  +-- Tool Registry
          |
          +-- Mireye MCP
          +-- USDA
          +-- Market
          +-- Listing
          +-- Geospatial
          +-- Valuation
```

Use structured outputs for every agent-to-agent exchange.

---

# 39. MCP Security

The Mireye credential must exist only server-side.

Never:

- expose it to browser JavaScript
- embed it in Next.js public variables
- return it in API responses
- log it
- include it in agent-visible application state unnecessarily

Use environment secrets.

---

# 40. Tool Security

Every agent tool must have:

```text
input schema
output schema
authorization policy
timeout
retry policy
source metadata
cost metadata
```

The orchestrator must validate tool arguments before execution.

---

# 41. Tool Registry

Implement:

```python
ToolDefinition(
    name="mireye.fetch_context",
    description="...",
    input_schema=...,
    output_schema=...,
    cost_model=...,
    provenance_required=True
)
```

The LLM selects tools.

The application validates and executes them.

Never allow the model to directly execute arbitrary HTTP requests.

---

# 42. Error Handling

Handle:

- invalid address
- unavailable listing
- listing blocked
- Mireye timeout
- Mireye malformed response
- external dataset unavailable
- conflicting datasets
- insufficient spatial coverage
- stale data
- valuation insufficient evidence
- agent loop exhaustion

The final result should degrade gracefully.

Example:

> Valuation confidence is low because comparable transaction evidence was insufficient.

Not:

> $1,237,452 estimated value

when there is no reliable basis.

---

# 43. Provenance Rules

Every important output must be traceable.

Implement:

```text
Decision
  -> reasons
  -> signals
  -> evidence
  -> source
```

Example:

```text
DO NOT ACQUIRE
    |
    +-- valuation mismatch
            |
            +-- estimated tillable footprint
                    |
                    +-- CDL observations
                    +-- Mireye context
```

The UI should allow users to navigate this chain.

---

# 44. Evidence Freshness

Store:

```text
retrieved_at
dataset_vintage
source_publication_date
```

Agents should prefer recent/relevant data but must respect dataset-specific temporal semantics.

Do not confuse retrieval date with data vintage.

---

# 45. Data Resolution Awareness

Every evidence source should carry:

```text
spatial_resolution
temporal_resolution
semantic_scope
```

The contradiction engine must use these.

This prevents false contradictions caused by comparing:

```text
parcel-level seller claim
vs
30m historical raster
```

as if they were measurements of exactly the same thing.

---

# 46. Evaluation Harness

Build an evaluation framework from the beginning.

Each case:

```json
{
  "case_id": "case_001",
  "input": "...",
  "buyer_context": {},
  "known_property_facts": {},
  "expected_claims": [],
  "expected_material_contradictions": [],
  "expected_decision": "...",
  "expected_valuation_range": {},
  "notes": []
}
```

Minimum target:

10–20 cases.

Evaluate:

```text
property resolution accuracy
claim extraction accuracy
material contradiction precision
material contradiction recall
evidence provenance completeness
valuation plausibility
decision correctness
unsupported-claim rate
false-certainty rate
investigation efficiency
```

---

# 47. Agent Evaluation

Add agent-specific metrics:

### Investigation quality

Did the agent investigate the uncertainty that mattered?

### Investigation efficiency

Did it waste calls?

### Decision stability

Would another low-value investigation materially change the result?

### Evidence discipline

Did every major claim have evidence?

### Contradiction discipline

Did it distinguish discrepancy from proof?

### Valuation discipline

Did it avoid unsupported numerical precision?

### Self-critique quality

Did the evidence critic identify weaknesses in the thesis?

---

# 48. Golden Evaluation Cases

Create cases deliberately covering:

1. Strong property, seller claims supported.
2. Strong property, exaggerated tillable acreage.
3. Flood risk hidden behind attractive listing.
4. Irrigation claim unsupported.
5. Historical agricultural continuity.
6. Land-use drift.
7. Soil/drainage conflict.
8. Good property but overpriced.
9. Poor property at attractive price.
10. Strong property with unresolved critical evidence.
11. Dataset-resolution false contradiction.
12. Missing listing information.
13. Invalid address.
14. External source unavailable.
15. Conflicting agricultural evidence.
16. Buyer preference changes verdict.
17. Valuation cannot be confidently bounded.
18. Property is good physically but poor economically.
19. Property is mediocre physically but cheap enough to acquire.
20. Evidence critic overturns initial thesis.

---

# 49. Testing

Unit tests:

```text
claim transitions
materiality
signal calculations
VOI
valuation calculations
provenance
input normalization
```

Integration tests:

```text
Mireye adapter
USDA adapters
listing ingestion
agent tool calls
database persistence
```

End-to-end:

```text
address -> investigation -> decision
URL -> investigation -> decision
natural language -> investigation -> decision
```

Failure tests:

```text
Mireye unavailable
external dataset unavailable
invalid listing
ambiguous address
insufficient evidence
agent exceeds loop limit
```

---

# 50. Observability

Implement structured logs.

Track:

```text
investigation_id
agent_run_id
agent_name
tool_name
latency
success/failure
source
cost
decision impact
```

Create an investigation trace visible to developers.

Do not expose hidden chain-of-thought.

---

# 51. Caching

Cache:

- geocoding
- Mireye context
- public dataset lookups
- market benchmarks

Cache keys must include relevant:

```text
coordinate
fields
dataset version
time period
geometry
```

Never serve stale evidence without indicating its vintage.

---

# 52. API Contracts

Example:

```http
POST /api/investigations
```

Request:

```json
{
  "input_type": "address|listing_url|query",
  "input": "...",
  "buyer_profile_id": "..."
}
```

Response:

```json
{
  "investigation_id": "...",
  "status": "queued"
}
```

Streaming:

```http
GET /api/investigations/{id}/events
```

Result:

```http
GET /api/investigations/{id}
```

Claims:

```http
GET /api/investigations/{id}/claims
```

Evidence:

```http
GET /api/investigations/{id}/evidence
```

Valuation:

```http
GET /api/investigations/{id}/valuation
```

Strategy:

```http
GET /api/investigations/{id}/strategy
```

---

# 53. Event Model

Use server-sent events or WebSockets.

Events:

```text
investigation.started
property.resolved
claims.extracted
agent.started
tool.started
tool.completed
evidence.added
signal.derived
contradiction.detected
materiality.assessed
investigation.selected
valuation.updated
decision.updated
strategy.generated
investigation.completed
investigation.failed
```

---

# 54. Frontend Design Principle

The interface should visually communicate:

> "The system is investigating."

not:

> "The AI is chatting."

Primary visual hierarchy:

```text
Decision
↓
Why
↓
What was discovered
↓
Evidence
↓
Valuation
↓
Risks
↓
Actions
```

---

# 55. Report Generation

Generate a structured report from the final world model.

Do not have the LLM regenerate facts independently.

Report generation should consume validated state:

```text
world_model
+
decision
+
valuation
+
strategy
```

The report renderer should never invent new facts.

---

# 56. No Fabrication Policy

Hard requirements:

Never fabricate:

- acreage
- soil
- crop history
- irrigation
- ownership
- water rights
- zoning
- legal status
- comparable sales
- market prices
- Mireye values
- citations

If missing:

```text
UNKNOWN
```

If inferred:

```text
INFERRED
```

If proxy:

```text
PROXY ONLY
```

If contradicted:

```text
CONTRADICTED
```

---

# 57. Legal/Property Rights Boundary

The system must never state that it has established:

- legal ownership
- legal access
- water rights
- easements
- title
- zoning legality
- legal agricultural rights

unless the product has an authoritative legal/title source.

Physical evidence may indicate a concern.

Correct:

> "The available physical evidence indicates potential access constraints."

Incorrect:

> "The property has no legal access."

---

# 58. Agent Prompt Architecture

Maintain prompts in version-controlled files.

```text
prompts/
├── orchestrator.md
├── property_agent.md
├── agriculture_agent.md
├── market_agent.md
├── critic_agent.md
├── strategy_agent.md
└── schemas/
```

Prompts should specify:

- role
- objective
- available state
- available tools
- forbidden assumptions
- output schema
- evidence requirements
- stopping behavior

Never put business logic solely in prompts.

---

# 59. Agent Output Example

Each specialist should return:

```json
{
  "assessment": "...",
  "claims": [],
  "signals": [],
  "contradictions": [],
  "unknowns": [],
  "recommended_actions": [],
  "evidence_ids": [],
  "confidence": 0
}
```

The orchestrator validates it.

---

# 60. Evidence Critic Prompt Principle

The critic should ask:

```text
What assumption is currently carrying the most decision weight?

What evidence would falsify it?

Are we comparing datasets with compatible resolution and vintage?

Are we treating a proxy as proof?

Is the valuation relying on unsupported precision?

Would the buyer's preferences change the materiality?

What is the strongest argument against the current verdict?
```

---

# 61. Demo Scenario

Build one polished demonstration around an agricultural listing with:

- explicit acreage
- tillable-acre claim
- asking price
- agricultural claims
- enough geographic context for Mireye
- historical crop evidence

Ideal narrative:

```text
1. Paste listing.
2. Agent extracts seller claims.
3. Agent identifies tillable acreage as valuation-critical.
4. Agent queries Mireye.
5. Agent queries historical crop data.
6. Derived signal shows divergence.
7. Materiality engine determines divergence is economically important.
8. Agent chooses additional investigation.
9. Agricultural agent refines the analysis.
10. Market agent recalculates valuation.
11. Evidence critic challenges thesis.
12. Strategy agent recommends a condition/renegotiation.
13. Final binary verdict appears.
```

The demo should visibly demonstrate the agent changing its investigation path.

---

# 62. Implementation Phases

## Phase 0 — Repository and infrastructure

Build:

- monorepo
- Docker
- environment configuration
- PostgreSQL/PostGIS
- FastAPI
- Next.js
- migrations
- CI
- linting
- tests

Acceptance:

- application runs locally
- database initializes
- frontend reaches backend
- health checks pass

## Phase 1 — Property ingestion

Build:

- address resolver
- URL ingestion
- natural-language parser
- property normalization
- claim extraction

Acceptance:

All three input modes create the same normalized investigation object.

## Phase 2 — World model

Build:

- investigation persistence
- claims
- evidence
- relationships
- state transitions
- provenance

Acceptance:

Every state change is traceable.

## Phase 3 — Mireye MCP

Build:

- MCP connection
- field discovery
- context retrieval
- evidence normalization
- citation preservation

Acceptance:

A real property can receive Mireye context and provenance.

## Phase 4 — Agricultural datasets

Build:

- CDL adapter
- SSURGO adapter
- agricultural enrichment

Acceptance:

Historical crop and soil evidence appear in the world model.

## Phase 5 — First autonomous loop

Build:

- orchestrator
- property agent
- agriculture agent
- tool selection
- state update
- loop
- stopping criteria

Acceptance:

Agent can autonomously discover an investigation path.

## Phase 6 — Contradiction + VOI

Build:

- contradiction engine
- materiality engine
- VOI engine
- next-action planner

Acceptance:

Agent investigates a material contradiction and skips immaterial discrepancies.

## Phase 7 — Market + valuation

Build:

- market adapters
- comparables
- valuation engine
- uncertainty ranges

Acceptance:

System produces an evidence-backed valuation.

## Phase 8 — Multi-agent critic + strategy

Build:

- market agent
- evidence critic
- strategy agent
- final decision synthesis

Acceptance:

System can challenge and update its own thesis.

## Phase 9 — Product UI

Build:

- investigation dashboard
- timeline
- evidence graph
- map
- valuation
- strategy
- buyer profile
- history

Acceptance:

Non-technical user can run and understand an investigation.

## Phase 10 — Evaluation

Build:

- 10–20 cases
- evaluator
- metrics
- failure reports

Acceptance:

Evaluation report generated automatically.

## Phase 11 — Hardening

Build:

- error handling
- security
- rate limiting
- observability
- caching
- deployment

Acceptance:

Production-like deployment works from a clean environment.

---

# 63. Codex Execution Rules

Codex Enterprise must:

1. Inspect the repository before changing anything.
2. Do not overwrite an existing working architecture without justification.
3. Build vertically, not as disconnected mock screens.
4. Implement real integrations rather than fake services.
5. Use typed contracts between frontend/backend/agents/tools.
6. Add tests alongside functionality.
7. Never hardcode external data as if it were live.
8. Never fabricate provider responses.
9. Keep provider integrations isolated.
10. Keep secrets server-side.
11. Preserve provenance.
12. Never expose chain-of-thought.
13. Make all agent state transitions observable.
14. Make all important numerical calculations deterministic.
15. Allow agents to choose investigation paths.
16. Do not reduce the system to a fixed pipeline.
17. Do not create an arbitrary final weighted score.
18. Do not use parcel-level Mireye fields unless genuinely necessary and economically justified.
19. Document every external dataset.
20. Document all assumptions.
21. Add evaluation cases before claiming the system is complete.

---

# 64. Definition of Done

The project is complete only when:

- A user can create a buyer profile.
- A user can submit an address.
- A user can submit a listing URL.
- A user can submit a natural-language property query.
- All three initiate independent investigations.
- The property is normalized.
- Seller claims are extracted.
- Mireye is accessed through MCP.
- External agricultural datasets are integrated.
- Evidence is persisted with provenance.
- Claims have explicit states.
- Derived signals are produced.
- Contradictions are detected.
- Materiality is assessed.
- The agent selects further investigations.
- The investigation can loop.
- The critic challenges the thesis.
- Valuation is calculated from evidence.
- Uncertainty is represented.
- Binary acquisition verdict is produced.
- Reasoning is traceable to evidence.
- Diligence recommendations are generated.
- Negotiation recommendations are generated.
- Buyer context is persisted.
- Investigation history is persisted.
- No fabricated facts are presented.
- The UI displays the live investigation.
- The final dossier is understandable without seeing the agent internals.
- 10–20 evaluation cases can be executed.
- Metrics are reported.
- The entire system can be deployed from documented configuration.

---

# 65. First Build Priority

Do NOT start by building the entire UI.

Build the smallest complete vertical slice:

```text
natural-language property query
        ↓
property resolution
        ↓
claim extraction
        ↓
Mireye MCP
        ↓
CDL
        ↓
claim/evidence graph
        ↓
contradiction
        ↓
VOI
        ↓
second investigation
        ↓
binary verdict
```

Once this works reliably, add valuation and strategy.

This vertical slice is the proof that the product is genuinely agentic.

---

# 66. Final Product Philosophy

The product should answer three questions:

### What is actually true about this land?

Evidence layer.

### What does that imply for this buyer?

Reasoning layer.

### What should the buyer do?

Decision/strategy layer.

The product should never collapse these into one opaque AI score.

The strongest demonstration is not:

> "We fetched 30 Mireye fields."

It is:

> "The seller's claim looked attractive. The agent identified the claim that mattered most to valuation, independently investigated it using Mireye and agricultural history, discovered a material divergence, recognized that the divergence could change the deal economics, investigated further, revised the valuation, and changed the acquisition recommendation."

That is the behavior the implementation must optimize for.

---

# 67. Codex Enterprise Master Instruction

Build the entire system described in this document end-to-end.

Start by inspecting the repository and existing environment. Then create a working vertical slice before expanding functionality.

Do not substitute a deterministic scoring pipeline for the agentic investigation loop.

The central autonomous behavior must be:

```text
Understand
→ hypothesize
→ investigate
→ enrich
→ compare
→ challenge
→ assess materiality
→ calculate value of information
→ investigate again when justified
→ stabilize thesis
→ value
→ decide
→ recommend action
```

Use Mireye through MCP.

Use OpenAI only inside the agent runtime.

Use specialized agents coordinated by an orchestrator.

Use deterministic code for calculations, validation, state transitions, provenance and numerical valuation mechanics.

Use agents for prioritization, hypothesis formation, tool selection, interpretation, contradiction discovery, investigation planning and strategy.

Never fabricate evidence.

Never claim certainty beyond the evidence.

Never treat a proxy as proof.

Never use an unexplained weighted score.

Never expose API keys.

Never expose hidden chain-of-thought.

Preserve source provenance through every derived conclusion.

Build the product as a real, deployable application, not a prototype notebook.

At every phase, write tests and verify the acceptance criteria before proceeding.

If a provider API differs from assumptions in this specification, inspect its actual documentation/tool schema and implement an adapter rather than inventing an API.

When external data is unavailable, explicitly represent the limitation and let the agent reason under uncertainty.

The final system must be capable of taking a real agricultural property and autonomously producing:

```text
PROPERTY REALITY
+
CLAIM/EVIDENCE ANALYSIS
+
AGRICULTURAL ANALYSIS
+
CONTRADICTIONS
+
MATERIAL RISKS
+
FINANCIAL VALUATION
+
ACQUISITION VERDICT
+
DUE DILIGENCE
+
NEGOTIATION STRATEGY
```

with every important conclusion traceable to evidence.
