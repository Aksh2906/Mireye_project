# Architecture

The application is organized as a Next.js web client and a FastAPI domain API. Provider-specific connectors are isolated behind typed tools. The investigation orchestrator reads and writes a durable world model and delegates domain proposals to specialist agents. All state mutations pass deterministic validators.

The reasoning boundary is intentional:

- Agents prioritize unknowns, propose hypotheses and tools, interpret evidence, and challenge conclusions.
- Code validates tool arguments, claim transitions, provenance, materiality factors, value-of-information arithmetic, valuation calculations, and circuit breakers.
- Reports consume validated world-model state and cannot introduce facts.

Provider failures become structured limitations. They never trigger synthetic evidence.
