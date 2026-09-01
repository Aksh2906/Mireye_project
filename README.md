# Mireye Agriculture Intelligence

Mireye Agriculture Intelligence is an evidence-first land acquisition platform for agricultural properties in the United States. It accepts an address, coordinates, a public listing URL, or a natural-language deal description and produces source-linked property, hazard, land-use, crop, alternatives, and investment analysis.

The system does not turn missing data into favorable assumptions. If a required provider or economic input is unavailable, the affected result is labeled as unavailable or `INSUFFICIENT_EVIDENCE`.

## Capabilities

- Resolve addresses, coordinates, listing URLs, and agricultural acquisition queries.
- Display farm locations and best-available boundaries on a Leaflet map with satellite and street layers.
- Retrieve deterministic terrain, soil, land-cover, infrastructure, utility, hazard, solar, wind, and land-use evidence from Mireye.
- Evaluate row crops, hay, grazing, cattle, dairy, sheep, goats, orchards, greenhouses, renewable energy, and mixed use.
- Rank crops and activities using evidence strength, suitability, risk, and sourced economics.
- Calculate operating ROI, cash-on-cash return, NPV, IRR, DSCR, payback, break-even values, and maximum defensible offer.
- Search authorized nearby land listings through RentCast or another configured listing feed.
- Preserve publisher, dataset, source URL, vintage, unit, confidence, spatial scope, and limitations for material observations.
- Produce Buy, Negotiate, Investigate, Pass, or Insufficient Evidence outcomes.

## Technology

| Layer | Technology |
|---|---|
| Web | Next.js 16, React 19, TypeScript |
| Map | Leaflet, Esri World Imagery, OpenStreetMap |
| API | FastAPI, Pydantic, SQLAlchemy |
| Local storage | SQLite |
| Production-compatible storage | PostgreSQL/PostGIS |
| Property intelligence | Mireye REST with optional Mireye MCP fallback |
| Listings | RentCast sale-listing API or a permitted JSON feed |
| Agricultural evidence | USDA Cropland Data Layer, SSURGO, NASS Quick Stats |
| Agent reasoning | OpenAI Responses API |

## How the system works

```text
User input
  -> input and objective resolver
  -> investigation candidates and value-of-information ranking
  -> Mireye, USDA, listing, market, parcel and economics connectors
  -> normalized evidence world model
  -> crop, activity, hazard, boundary and finance engines
  -> evidence critic and decision synthesis
  -> map, evidence, uses, economics, hazards, alternatives and dossier pages
```

The investigation loop repeatedly selects the available action most likely to change the acquisition decision. Tool results are normalized into evidence, derived signals are recalculated, contradictions and unknowns are registered, and the loop stops when useful actions or configured budgets are exhausted. Deterministic calculations run outside the language model.

## Local requirements

Install these tools before setup:

- Git
- Python 3.12
- Node.js 22 or newer
- npm
- GNU Make for the one-command scripts

Confirm the versions:

```bash
git --version
python3.12 --version
node --version
npm --version
make --version
```

## Quick local setup

Clone the repository and install the API and web dependencies:

```bash
git clone https://github.com/Aksh2906/Mireye_project.git
cd Mireye_project
make setup
```

`make setup` performs the following local operations:

1. Creates `.venv` with Python 3.12.
2. Installs the API dependencies from `apps/api/requirements-local.txt`.
3. Installs the web dependencies from `apps/web/package.json`.
4. Creates a private, empty `.env` with mode `600` if one does not exist.
5. Runs the local environment doctor.

Both `.env` and `.env.example` are excluded from Git. The repository intentionally does not ship an environment template; use the configuration below to populate your local `.env` without committing credentials.

## Local environment configuration

Open the root `.env` file and add the services you want to use:

```dotenv
APP_ENV=development
APP_API_KEY=

DATABASE_URL=sqlite+pysqlite:///./mireye.sqlite3

OPENAI_API_KEY=
OPENAI_MODEL=gpt-5.6-sol
OPENAI_REASONING_EFFORT=medium

MIREYE_API_URL=https://api.mireye.com
MIREYE_API_TOKEN=
MIREYE_MCP_URL=https://api.mireye.com/mcp
MIREYE_MCP_TOKEN=

GEOCODER_BASE_URL=https://nominatim.openstreetmap.org
CDL_SERVICE_URL=https://nassgeodata.gmu.edu/axis2/services/CDLService/GetCDLValue
SSURGO_SERVICE_URL=https://sdmdataaccess.sc.egov.usda.gov/Tabular/post.rest
NASS_QUICKSTATS_BASE_URL=https://quickstats.nass.usda.gov/api/api_GET/
NASS_QUICKSTATS_API_KEY=

LISTING_SEARCH_URL=https://api.rentcast.io/v1/listings/sale
LISTING_API_TOKEN=

MARKET_BENCHMARK_URL=
MARKET_COMPARABLES_URL=
AGRICULTURE_ECONOMICS_URL=
AGRICULTURE_ECONOMICS_TOKEN=
PARCEL_API_URL=
PARCEL_API_TOKEN=
HAZARD_API_URL=
HAZARD_API_TOKEN=

NEXT_PUBLIC_API_URL=http://localhost:8000
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

MAX_AGENT_TURNS=12
MAX_TOOL_CALLS=30
MAX_EXTERNAL_REQUESTS=30
MAX_WALL_CLOCK_SECONDS=180
```

Do not add any server credential to a variable beginning with `NEXT_PUBLIC_`; those values are included in browser code.

### Provider configuration

| Setting | Needed for | Where to obtain it |
|---|---|---|
| `OPENAI_API_KEY` | Agent-selected investigations, specialist analysis, critic, and strategy | An API project key from the [OpenAI API dashboard](https://platform.openai.com/api-keys) |
| `MIREYE_API_TOKEN` | Hosted Mireye `/v1/fetch`, `/v1/ask`, and `/v1/meta/fields` calls | Mireye account or service administrator |
| `MIREYE_MCP_TOKEN` | Optional Mireye MCP fallback | Mireye account or service administrator |
| `NASS_QUICKSTATS_API_KEY` | USDA regional agricultural value benchmarks | USDA NASS Quick Stats API registration |
| `LISTING_API_TOKEN` | Nearby active land listings | RentCast API account; the adapter sends this value as `X-Api-Key` |
| `MARKET_BENCHMARK_URL` | Regional value-per-acre evidence | A licensed market-data service matching the documented contract |
| `MARKET_COMPARABLES_URL` | Transaction-level comparable sales | A licensed comparable-sales service |
| `AGRICULTURE_ECONOMICS_URL` | Sourced crop and alternative-use profitability assumptions | A maintained enterprise-budget service |
| `PARCEL_API_URL` | Authoritative parcel geometry | A licensed parcel provider or supported county GIS gateway |
| `HAZARD_API_URL` | Optional supplemental hazard observations | An approved spatial hazard provider |

Mireye is the primary source for disaster and physical-land intelligence. `HAZARD_API_URL` is supplemental and can remain blank. Profitability is calculated only when traceable production, price, and cost inputs are available; sourced assumptions may also be entered from the Economics page.

## Validate and start

Check the local installation:

```bash
make doctor
```

Start the API and web application together:

```bash
make dev
```

Open these local URLs:

- Application: [http://localhost:3000](http://localhost:3000)
- API documentation: [http://localhost:8000/docs](http://localhost:8000/docs)
- Health endpoint: [http://localhost:8000/health](http://localhost:8000/health)

Stop both services with `Ctrl+C`.

### Run services separately

Terminal 1:

```bash
make api-dev
```

Terminal 2:

```bash
make web-dev
```

## Manual setup

Use this path if `make` is unavailable.

### macOS or Linux

From the repository root:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r apps/api/requirements-local.txt
npm install --prefix apps/web
touch .env
chmod 600 .env
```

Start the API:

```bash
PYTHONPATH=apps/api .venv/bin/python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

In a second terminal, start the web application:

```bash
npm --prefix apps/web run dev -- --hostname 127.0.0.1
```

### Windows PowerShell

From the repository root:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r apps/api/requirements-local.txt
npm install --prefix apps/web
New-Item -Path .env -ItemType File -Force
```

Start the API:

```powershell
$env:PYTHONPATH="apps/api"
.venv\Scripts\python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

In a second PowerShell window:

```powershell
npm --prefix apps/web run dev -- --hostname 127.0.0.1
```

## Run an investigation

1. Open `http://localhost:3000/profile` and create an optional buyer profile.
2. Return to the home page.
3. Choose address, coordinates, listing URL, or natural-language query.
4. Enter a resolvable property and provide the acquisition objective, budget, risk tolerance, and intended uses.
5. Start the investigation and wait for the evidence loop to complete.
6. Review the boundary scope before treating an observation as parcel-wide.
7. Open the Uses, Economics, Hazards, Alternatives, Evidence, and Dossier pages.
8. Add sourced economic assumptions if the decision remains `INSUFFICIENT_EVIDENCE` because profitability inputs are missing.

## Mireye integration

The application uses:

| Endpoint | Use |
|---|---|
| `GET /v1/meta/fields` | Discover and validate supported Mireye field names |
| `POST /v1/fetch` | Retrieve deterministic hazard, terrain, soil, infrastructure, utility, solar, wind, boundary, and land-use fields |
| `POST /v1/ask` | Retrieve source-backed narrative context when useful |
| `/mcp` | Optional MCP transport and fallback integration |

Field-level failures remain visible. Physical or raster geometry is never presented as a legal survey or ownership determination.

## Listing integration

With `LISTING_SEARCH_URL=https://api.rentcast.io/v1/listings/sale`, the application searches active `Land` listings by coordinate and radius, normalizes price and acreage, deduplicates canonical source URLs, and compares the strongest alternatives. Provider outages degrade to an explicit unavailable state instead of failing the investigation.

## Boundary priority

The map chooses geometry in this order:

1. Listing geometry.
2. Authoritative parcel geometry.
3. User-uploaded geometry.
4. User-drawn geometry.
5. Clearly labeled acreage-equivalent analysis geometry.

## Quality checks

Run the full local verification suite from the repository root:

```bash
make lint
make test
make eval
```

Verify the production web build:

```bash
cd apps/web
npm run lint
npm run build
```

The evaluation runner writes `evaluation/reports/latest.json` and `evaluation/reports/failures.json`.

## Common problems

### `make setup` cannot find Python

Install Python 3.12 and confirm `python3.12 --version` works in the same terminal. The automated setup deliberately requires that exact command.

### Web application cannot reach the API

Confirm these values in `.env`, then restart the web application:

```dotenv
NEXT_PUBLIC_API_URL=http://localhost:8000
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

### API returns 401

For ordinary local browser development, leave `APP_API_KEY` blank. If it is set, API requests must send its value as a bearer token.

### Mireye is unavailable

Confirm `MIREYE_API_URL`, `MIREYE_API_TOKEN`, and network access. Test field discovery without exposing the token in command history:

```bash
curl -i -H "Authorization: Bearer $MIREYE_API_TOKEN" "$MIREYE_API_URL/v1/meta/fields"
```

Restart the API after editing `.env`.

### OpenAI assessments are absent

Confirm the root `.env` contains `OPENAI_API_KEY`, the API project has billing or credits, the selected model is available, and the API was restarted after the change. Deterministic analysis continues when model calls are unavailable.

### Investigation reports insufficient evidence

Check the Evidence and Economics pages for the exact missing fields. Common causes are:

- no authoritative boundary or usable listing geometry;
- missing production, commodity price, or operating-cost assumptions;
- missing market benchmark or comparable-sale sources;
- unavailable Mireye fields or invalid Mireye credentials;
- no matching listings from the configured listing provider.

Add traceable provider data or sourced assumptions and rerun the affected analysis. The system intentionally does not invent the missing values.

## Repository structure

- `apps/api/app` — API routes, connectors, agent runtime, world model, and deterministic engines
- `apps/api/tests` — API, connector, engine, and end-to-end tests
- `apps/web` — Next.js application and Leaflet map UI
- `docs` — architecture, provider, evaluation, and implementation documentation
- `evaluation` — golden cases, runner, and generated reports
- `infrastructure/migrations` — PostgreSQL/PostGIS schema migrations
- `scripts` — local setup, diagnostics, and development launch scripts
- `SETUP_GUIDE.md` — focused local installation and troubleshooting guide

