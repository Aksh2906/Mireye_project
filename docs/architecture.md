# Architecture

The application is organized as a Next.js web client and a FastAPI domain API. Provider-specific connectors are isolated behind typed tools. The investigation orchestrator reads and writes a durable world model and delegates domain proposals to specialist agents. All state mutations pass deterministic validators.

The reasoning boundary is intentional:

- Agents prioritize unknowns, propose hypotheses and tools, interpret evidence, and challenge conclusions.
- Code validates tool arguments, claim transitions, provenance, materiality factors, value-of-information arithmetic, valuation calculations, and circuit breakers.
- Reports consume validated world-model state and cannot introduce facts.

V2 persists the planner-facing state explicitly: buyer objective, hypotheses, candidate and executed actions, investigation budget, iteration count, termination reason, agricultural opportunities, sourced economic scenarios, activity-specific hazards, and alternatives. The model selects what to investigate; deterministic services validate geometry, normalize data, calculate VoI and economics, update state, and preserve provenance.

The loop is `observe → hypothesize → identify uncertainty → estimate materiality → select the highest-value action → execute → enrich → reduce state → revise`. It stops when no positive-value action remains, decision stability is sufficient, or a configured safety budget is reached. It does not fetch a fixed field bundle or calculate an opaque master score.

Provider failures become structured limitations. They never trigger synthetic evidence.
