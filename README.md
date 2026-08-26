# Farm Acquire

An evidence-first, autonomous agricultural property acquisition investigation system. It accepts an address, listing URL, or natural-language property description; preserves claims and source provenance; selects investigations using value of information; and returns a binary acquisition verdict, valuation range, diligence plan, and negotiation strategy.

## Quick start without Docker

Python 3.12 and Node.js 22+ are required.

```bash
make setup
make doctor
make dev
```

Then open `http://localhost:3000`; API documentation is at `http://localhost:8000/docs`. The local workflow uses SQLite and does not require PostgreSQL or Docker.

To run one service at a time:

```bash
make api-dev
make web-dev
```

Docker remains available later with `make dev-docker`.

The system never substitutes fabricated provider data. Missing credentials and unavailable datasets are represented as explicit limitations. See [docs/architecture.md](docs/architecture.md) and [docs/providers.md](docs/providers.md).

For complete installation instructions, required and optional credentials, provider response contracts, and troubleshooting, see [SETUP_GUIDE.md](SETUP_GUIDE.md).

## Verification and deployment

Run `make lint`, `make test`, and `make eval` before deployment. The production-like stack is defined in `docker-compose.yml`: PostGIS initializes from `infrastructure/migrations`, the API waits for database health, and the web app waits for API health. Set `APP_API_KEY` at an ingress/API boundary, use non-default database credentials, and provide HTTPS termination in the deployment environment.

Live provider acceptance requires valid Mireye MCP, OpenAI, and configured market-provider credentials. USDA CDL and SSURGO remain independently configurable. Every unavailable provider degrades to an explicit limitation rather than synthetic evidence.
