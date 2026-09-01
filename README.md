# Mireye Agriculture Intelligence

Evidence-first decision intelligence for agricultural land acquisition in the United States. The application accepts an address, coordinates, a public listing URL, or a natural-language deal description and produces source-linked analysis instead of an opaque property score.

## What it does

- Resolves the property location and best available analysis boundary.
- Displays the property in Leaflet using satellite and street basemaps.
- Retrieves deterministic, provenance-bearing physical and hazard fields from Mireye.
- Evaluates crops, grazing, cattle, dairy, sheep, goats, hay, orchards, greenhouses, solar, wind, and mixed use.
- Models operating scenarios, financing, ROI, NPV, IRR, payback, and maximum defensible offer when sourced economics are available.
- Searches authorized nearby land listings through RentCast and compares shortlisted alternatives.
- Preserves source, dataset, URL, vintage, unit, confidence, spatial scope, and limitations for every material observation.
- Returns Buy, Investigate, Negotiate, Pass, or Insufficient Evidence without inventing missing data.

## Technology

| Layer | Technology |
|---|---|
| Web application | Next.js 16, React 19, TypeScript |
| Mapping | Leaflet, Esri World Imagery, OpenStreetMap |
| API | FastAPI, Pydantic, SQLAlchemy |
| Local database | SQLite |
| Production database | PostgreSQL/PostGIS |
| Property intelligence | Mireye REST and optional MCP |
| Listing discovery | RentCast sale-listing API or another authorized JSON feed |
| Agricultural data | USDA Cropland Data Layer, SSURGO, NASS Quick Stats |
| Agent reasoning | OpenAI API with deterministic calculation engines outside the model |

## System flow

```text
User input
  -> input and objective resolver
  -> evidence-first investigation loop
  -> Mireye, USDA, market and listing connectors
  -> normalized evidence world model
  -> crop, activity, hazard and finance engines
  -> critic and decision synthesis
  -> map, evidence, economics, hazards, alternatives and dossier views
```

The agent loop ranks possible investigations by expected decision value, executes the most useful available tool, normalizes results into evidence, recalculates derived signals, and stops when useful tools or configured budgets are exhausted. Provider failures become explicit data gaps; they never become favorable assumptions.

## Requirements

- Python 3.12+
- Node.js 22+
- npm
- Optional: Docker and Docker Compose for the PostGIS stack

## Local setup

```bash
git clone https://github.com/Aksh2906/Mireye_project.git
cd Mireye_project
make setup
```

Create a local `.env` file. Environment files are intentionally excluded from Git. Configure only the services you intend to use:

```dotenv
APP_ENV=development
DATABASE_URL=sqlite+pysqlite:///./mireye.sqlite3

OPENAI_API_KEY=
OPENAI_MODEL=gpt-5.6-sol
OPENAI_REASONING_EFFORT=medium

MIREYE_API_URL=https://api.mireye.com
MIREYE_API_TOKEN=
MIREYE_MCP_URL=https://api.mireye.com/mcp
MIREYE_MCP_TOKEN=

NASS_QUICKSTATS_API_KEY=
LISTING_SEARCH_URL=https://api.rentcast.io/v1/listings/sale
LISTING_API_TOKEN=

AGRICULTURE_ECONOMICS_URL=
AGRICULTURE_ECONOMICS_TOKEN=
MARKET_BENCHMARK_URL=
MARKET_COMPARABLES_URL=
PARCEL_API_URL=
PARCEL_API_TOKEN=
HAZARD_API_URL=
HAZARD_API_TOKEN=

NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

Never commit real credentials. Mireye is the primary disaster-intelligence provider; `HAZARD_API_URL` is only an optional supplemental source. An agricultural economics provider is optional because sourced assumptions can also be entered from the Economics page.

Validate and run:

```bash
make doctor
make dev
```

Open:

- Web application: [http://127.0.0.1:3000](http://127.0.0.1:3000)
- API documentation: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- API health: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

Run services separately when needed:

```bash
make api-dev
make web-dev
```

## Using the application

1. Choose an address, coordinates, listing URL, or deal-description input.
2. Select the acquisition objective, risk tolerance, budget, and optional buyer profile.
3. Start the investigation and wait for the evidence loop to complete.
4. Review the map and boundary scope before treating any result as parcel-wide.
5. Run use evaluation, disaster analysis, and nearby-listing discovery from their dedicated pages.
6. Add a sourced enterprise budget under Economics when ROI inputs are not supplied by a configured provider.
7. Review evidence limitations and priority diligence before relying on the recommendation.

## Provider behavior

### Mireye

The application uses `/v1/fetch` for deterministic hazard, terrain, soil, infrastructure, utility, solar, wind, and land-use fields. `/v1/ask` is retained for source-backed narrative context, while `/v1/meta/fields` supports catalog validation. Field-level partial failures remain visible.

### Listings

RentCast is supported through `LISTING_SEARCH_URL`. The adapter sends its credential as `X-Api-Key`, searches active `Land` records by coordinate and radius, and converts lot square footage to acres. A licensed rural-land or local MLS/RESO feed can replace it through the generic listing-provider contract.

### Boundaries

Boundary priority is listing geometry, authoritative parcel geometry, uploaded/drawn geometry, then an explicitly labeled acreage-equivalent analysis shape. No displayed geometry is represented as a legal survey or ownership determination.

### Economics

Profitability is calculated only when yield or production, price, and operating cost have traceable sources. Missing economic inputs result in `INSUFFICIENT_EVIDENCE`; the system does not fabricate ROI.

## Verification

```bash
make lint
make test
make eval
```

The web application can also be verified independently:

```bash
cd apps/web
npm run lint
npm run build
```

## Docker

```bash
make dev-docker
```

Docker Compose starts PostGIS, applies migrations from `infrastructure/migrations`, waits for API health, and then starts the web application. Configure non-default database credentials and HTTPS termination before deployment.

## Repository guide

- `apps/api/app` — API, connectors, agent runtime and calculation engines
- `apps/api/tests` — API and domain tests
- `apps/web` — Next.js user interface
- `docs` — architecture, providers, evaluation and implementation status
- `evaluation` — cases and evaluation runner
- `infrastructure/migrations` — database migrations
- `SETUP_GUIDE.md` — detailed provider contracts and troubleshooting

## Safety and scope

This software is decision support, not an appraisal, legal survey, title opinion, tax opinion, lending commitment, or guarantee of agricultural performance. Verify material facts with qualified local professionals before acquiring or improving property.
