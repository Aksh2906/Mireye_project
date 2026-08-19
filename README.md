# Mireye Agricultural Acquisition Intelligence

An evidence-first, autonomous agricultural property acquisition investigation system. It accepts an address, listing URL, or natural-language property description; preserves claims and source provenance; selects investigations using value of information; and returns a binary acquisition verdict, valuation range, diligence plan, and negotiation strategy.

## Quick start

1. Copy `.env.example` to `.env` and configure provider credentials.
2. Run `docker compose up --build`.
3. Open `http://localhost:3000`; API documentation is at `http://localhost:8000/docs`.

For local API development:

```bash
python3 -m venv .venv
.venv/bin/pip install -e 'apps/api[dev]'
PYTHONPATH=apps/api .venv/bin/uvicorn app.main:app --reload
```

The system never substitutes fabricated provider data. Missing credentials and unavailable datasets are represented as explicit limitations. See [docs/architecture.md](docs/architecture.md) and [docs/providers.md](docs/providers.md).

For complete installation instructions, required and optional credentials, provider response contracts, and troubleshooting, see [SETUP_GUIDE.md](SETUP_GUIDE.md).

## Verification and deployment

Run `make lint`, `make test`, and `make eval` before deployment. The production-like stack is defined in `docker-compose.yml`: PostGIS initializes from `infrastructure/migrations`, the API waits for database health, and the web app waits for API health. Set `APP_API_KEY` at an ingress/API boundary, use non-default database credentials, and provide HTTPS termination in the deployment environment.

Live provider acceptance requires valid Mireye MCP, OpenAI, and configured market-provider credentials. USDA CDL and SSURGO remain independently configurable. Every unavailable provider degrades to an explicit limitation rather than synthetic evidence.
