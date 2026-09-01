# Farm Acquire setup guide

This guide covers two ways to run the project:

1. **Local development setup (recommended for now):** runs FastAPI and Next.js directly with SQLite.
2. **Docker setup:** runs Next.js, FastAPI, PostgreSQL, and PostGIS together when Docker is available.

The application starts without external credentials. Without provider credentials, unavailable evidence is recorded as a limitation and the application does not fabricate replacement data.

## 1. Prerequisites

For the local setup, install:

- Python 3.12
- Node.js 22 or newer and npm
- Git

For the Docker setup, install:

- Docker Desktop with Docker Compose v2
- Git
- At least 4 GB of free memory for the stack

Check your tools:

```bash
docker --version
docker compose version
python3 --version
node --version
npm --version
```

## 2. Create the environment file

From the project root:

```bash
cp .env.example .env
```

The `.env` file is ignored by Git. Never commit it or paste its secrets into frontend code.

### Copy-ready local configuration

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

MARKET_BENCHMARK_URL=
MARKET_COMPARABLES_URL=
AGRICULTURE_ECONOMICS_URL=
AGRICULTURE_ECONOMICS_TOKEN=
LISTING_SEARCH_URL=https://api.rentcast.io/v1/listings/sale
LISTING_API_TOKEN=
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

## 3. Which keys and URLs are needed?

| Setting | Required to boot? | Required for | Where it comes from |
|---|---:|---|---|
| `OPENAI_API_KEY` | No | Agent-selected investigations, specialist assessments, critic, and strategy assessment | Create a project API key in the [OpenAI API dashboard](https://platform.openai.com/api-keys) and ensure API billing/credits are configured |
| `OPENAI_MODEL` | No | Selecting the OpenAI model | Defaults to `gpt-5.6-sol`; `gpt-5.6-terra` is a lower-cost alternative |
| `OPENAI_REASONING_EFFORT` | No | Model reasoning depth | Keep `medium` initially; supported values depend on the chosen model |
| `MIREYE_API_URL` | No | Deterministic hazard and land-use evidence through `/v1/fetch`, plus optional `/v1/ask` context | Use `https://api.mireye.com` for the hosted service |
| `MIREYE_API_TOKEN` | Yes for hosted Mireye | Authenticating to the Mireye REST API | Bearer token supplied by Mireye |
| `MIREYE_MCP_URL` | No | Optional MCP fallback | Use `https://api.mireye.com/mcp` for the hosted MCP service; do not use the host root |
| `MIREYE_MCP_TOKEN` | Sometimes | Authenticating to Mireye MCP, and fallback auth when `MIREYE_API_TOKEN` is blank | Bearer token supplied by Mireye |
| `NASS_QUICKSTATS_API_KEY` | Yes for the built-in benchmark | Latest USDA state farm-real-estate value per acre | Request a key from the USDA NASS Quick Stats API page |
| `MARKET_BENCHMARK_URL` | No | Regional value-per-acre evidence | A market-data API that you operate or license, matching the contract below |
| `MARKET_COMPARABLES_URL` | No | Comparable agricultural transactions | A market-data API that you operate or license, matching the contract below |
| `AGRICULTURE_ECONOMICS_URL` | No | Sourced crop, dairy, livestock, and other activity profitability | A maintained enterprise-budget/economics API matching the contract below |
| `AGRICULTURE_ECONOMICS_TOKEN` | Sometimes | Economics provider authentication | Bearer token supplied by the provider |
| `LISTING_SEARCH_URL` | No | Adaptive nearby land-listing search and candidate analysis | RentCast defaults to `https://api.rentcast.io/v1/listings/sale`; a licensed rural/MLS feed can replace it |
| `LISTING_API_TOKEN` | Yes for RentCast search | Listing feed authentication | RentCast API key (sent as `X-Api-Key`) or credentials supplied by the chosen provider |
| `PARCEL_API_URL` | No | Authoritative parcel-geometry lookup | A licensed parcel service or supported county GIS gateway |
| `PARCEL_API_TOKEN` | Sometimes | Parcel endpoint authentication | Bearer token supplied by the parcel provider |
| `HAZARD_API_URL` | No | Property-specific disaster/hazard observations | An approved spatial hazard service matching the contract below |
| `HAZARD_API_TOKEN` | Sometimes | Hazard endpoint authentication | Bearer token supplied by the hazard provider |
| `APP_API_KEY` | No | Optional bearer protection for `/api/*` | Generate your own strong secret; leave blank for the current direct-browser local UI |
| `DATABASE_URL` | Yes outside Compose | Persistent storage | Compose supplies PostGIS automatically; local development can use SQLite |
| USDA and geocoder URLs | No keys | Crop history, soil context, and address resolution | Public defaults are already configured |

### OpenAI setup

1. Open the [OpenAI API key page](https://platform.openai.com/api-keys).
2. Create a project-scoped secret key and copy it when shown.
3. Configure API billing or credits for that project.
4. Put the key only in the server-side `.env` file:

```dotenv
OPENAI_API_KEY=your_secret_key_here
OPENAI_MODEL=gpt-5.6-sol
OPENAI_REASONING_EFFORT=medium
```

OpenAI recommends using the `OPENAI_API_KEY` environment variable. This application calls OpenAI only from the FastAPI agent runtime; it must never be added to `NEXT_PUBLIC_*` variables or browser code.

If cost is more important than maximum reasoning quality, try:

```dotenv
OPENAI_MODEL=gpt-5.6-terra
```

### Mireye setup

The hosted REST integration is the simplest setup. Hazard analysis and use
evaluation call `/v1/fetch` with exact catalog field names and preserve each
field's source, URL, vintage, unit, confidence, and partial failure. `/v1/ask`
remains available for narrative context:

```dotenv
MIREYE_API_URL=https://api.mireye.com
MIREYE_API_TOKEN=your_bearer_token
```

The adapter can instead use Streamable HTTP MCP when `MIREYE_API_URL` is blank:

```dotenv
MIREYE_API_URL=
MIREYE_MCP_URL=https://api.mireye.com/mcp
MIREYE_MCP_TOKEN=your_optional_bearer_token
```

At runtime the adapter performs MCP `initialize` and `tools/list`, then discovers tools by their names and descriptions. For complete functionality, the server should expose tools corresponding to:

- property/context retrieval;
- field catalog/discovery;
- quote retrieval, if billed fields require a quote;
- batch context retrieval, if supported.

The adapter preserves the provider tool name, exact arguments, structured response fields, geometry, and source limitations. Property-level cultivated acreage is accepted as a property footprint only when Mireye returns property-scope metadata plus Polygon or MultiPolygon geometry.

### Market benchmark API contract

The built-in and recommended benchmark is USDA NASS Quick Stats. Configure:

```dotenv
NASS_QUICKSTATS_BASE_URL=https://quickstats.nass.usda.gov/api/api_GET/
NASS_QUICKSTATS_API_KEY=your_usda_nass_key
MARKET_BENCHMARK_URL=
```

The connector retrieves the newest state-level annual `AG LAND, INCL BUILDINGS`
asset value measured in dollars per acre. It is retained as a broad state benchmark
with an explicit limitation that it is not county-specific or a property appraisal.

`MARKET_BENCHMARK_URL` is an optional override for a licensed or internally hosted
provider. When set, it takes precedence over USDA NASS and receives a `GET` request
with `state` and `county` query parameters. It should return:

```json
{
  "value_per_acre": 7200,
  "unit": "USD/acre",
  "confidence": 0.7,
  "temporal_resolution": "2026 annual",
  "semantic_scope": "county agricultural land benchmark",
  "limitations": ["Regional benchmark; not a property appraisal."],
  "source": {
    "publisher": "Your licensed provider",
    "dataset": "County land values",
    "url": "https://provider.example/source-record",
    "vintage": "2026"
  },
  "raw_reference": {
    "record_id": "benchmark-123"
  }
}
```

`value_per_acre` is required. Do not return a value without publisher/dataset provenance.

### Market comparables API contract

`MARKET_COMPARABLES_URL` receives a `GET` request with `state`, `county`, and `acreage`. It should return:

```json
{
  "source": {
    "publisher": "Your licensed provider",
    "dataset": "Agricultural comparable sales",
    "url": "https://provider.example",
    "vintage": "2026-08"
  },
  "comparables": [
    {
      "location": "Example County, IA",
      "sale_price": 690000,
      "acreage": 100,
      "sale_date": "2026-05-15",
      "source_url": "https://provider.example/sales/abc",
      "confidence": 0.75,
      "adjustments": ["Similar acreage; location adjustment still required"],
      "limitations": ["Arm's-length status requires confirmation"]
    }
  ]
}
```

`sale_price` and `acreage` are required for each sale. The API calculates price per acre deterministically.

### Agricultural economics API contract

`AGRICULTURE_ECONOMICS_URL` receives a JSON POST containing state, county,
requested activities, and crop candidates. It returns provenance-bearing assumptions:

```json
{
  "source": {
    "publisher": "University extension or licensed provider",
    "dataset": "Regional enterprise budgets",
    "url": "https://provider.example/methodology",
    "vintage": "2026",
    "geography": "Iowa planning region"
  },
  "assumptions": [
    {
      "id": "corn-2026",
      "activity": "corn",
      "yield_per_acre": 195,
      "commodity_price": 4.8,
      "operating_cost_per_acre": 610,
      "units": {
        "yield_per_acre": "bushels/acre",
        "commodity_price": "USD/bushel",
        "operating_cost_per_acre": "USD/acre"
      },
      "confidence": 0.75,
      "geography": "Iowa planning region",
      "vintage": "2026",
      "limitations": ["Planning budget; replace with operator-specific bids and practices."]
    }
  ]
}
```

Dairy and livestock may provide `productive_units`/`herd_size`,
`production_per_unit`/`milk_yield_per_head`, `price_per_unit`, and
`operating_cost_per_unit`/`operating_cost_per_head`. The engine refuses to rank
profitability unless the production, price, and cost contract is complete.

### Nearby listing API contract

The checked-in default is RentCast's authorized sale-listing endpoint:

```dotenv
LISTING_SEARCH_URL=https://api.rentcast.io/v1/listings/sale
LISTING_API_TOKEN=your_rentcast_api_key
```

The adapter sends `X-Api-Key`, searches `propertyType=Land`, uses coordinate/radius
search, and converts RentCast `lotSize` square feet to acres. RentCast documents
more limited coverage for large rural and agricultural properties, so a licensed
local MLS/RESO or specialist land feed is preferable for production completeness.

For any other configured provider, the generic contract is:

`LISTING_SEARCH_URL` receives a `GET` request with `latitude`, `longitude`,
`radius_miles`, and optional price/acreage filters. It must be an API/feed you are
authorized to use. The response is either an array or `{ "listings": [...] }`:

```json
{
  "listings": [
    {
      "id": "provider-123",
      "source": "Licensed rural listing feed",
      "source_url": "https://provider.example/listings/123",
      "title": "120-acre farm",
      "price": 780000,
      "acreage": 120,
      "latitude": 42.01,
      "longitude": -93.02,
      "county": "Example County",
      "state": "IA",
      "description": "Provider-authorized listing text",
      "claimed_features": ["fenced", "well"],
      "source_timestamp": "2026-08-29T00:00:00Z"
    }
  ]
}
```

`id`, `source_url`, latitude, and longitude are required for discovery. Listing
claims are not treated as verified evidence.

### Parcel boundary API contract

`PARCEL_API_URL` receives `latitude` and `longitude` query parameters and returns:

```json
{
  "geometry": {"type": "Polygon", "coordinates": []},
  "source_name": "Licensed parcel provider",
  "source_url": "https://provider.example/parcel/123",
  "confidence": 0.85,
  "limitations": ["Assessor/GIS geometry; not a legal survey."]
}
```

The API validates and closes rings, calculates geodesic acreage, and compares it
with claimed acreage. It always labels the result as non-legal geometry.

### Hazard API contract

`HAZARD_API_URL` receives a JSON POST with `latitude`, `longitude`, requested
`hazards`, and optional GeoJSON `geometry`. It returns source metadata and hazard
observations:

```json
{
  "source": {
    "publisher": "Approved hazard provider",
    "dataset": "Property hazard context",
    "url": "https://provider.example/methodology",
    "vintage": "2026"
  },
  "hazards": [
    {
      "id": "flood-123",
      "hazard": "flood",
      "exposure": "high",
      "affected_area_acres": 18.4,
      "confidence": 0.8,
      "geometry": {"type": "Polygon", "coordinates": []},
      "spatial_resolution": "provider-defined",
      "limitations": ["Screening layer; confirm with site-specific diligence."]
    }
  ]
}
```

An empty or unavailable response remains unknown and is not interpreted as no
hazard exposure.

### Optional application API key

`APP_API_KEY` enables bearer authentication on every `/api/*` route:

```dotenv
APP_API_KEY=replace_with_a_long_random_secret
```

Generate a local secret with:

```bash
openssl rand -hex 32
```

The current browser UI calls the API directly and does not store a secret, so leave `APP_API_KEY` blank during ordinary local UI development. For API-only access, send:

```bash
curl http://localhost:8000/api/investigations \
  -H "Authorization: Bearer replace_with_a_long_random_secret"
```

For production browser authentication, place the application behind your identity-aware gateway or add a server-side session/proxy layer. Never expose `APP_API_KEY` through a `NEXT_PUBLIC_*` variable.

## 4. Run locally without Docker (recommended)

Install all dependencies once:

```bash
make setup
make doctor
```

Start the API and web application together:

```bash
make dev
```

The command starts:

- FastAPI at `http://localhost:8000`;
- Next.js at `http://localhost:3000`;
- a local SQLite database at `mireye.sqlite3`.

Press `Ctrl+C` once to stop both services cleanly.

To run the services in separate terminals:

```bash
make api-dev
```

```bash
make web-dev
```

## 5. Run with Docker later

Start Docker Desktop first, then from the repository root run:

```bash
docker compose up --build
```

The first build can take several minutes. Compose starts:

- PostGIS on the internal Docker network;
- FastAPI at `http://localhost:8000`;
- Next.js at `http://localhost:3000`.

The database migration in `infrastructure/migrations/001_initial.sql` runs automatically only when the Postgres volume is first created.

Verify the stack:

```bash
curl http://localhost:8000/health
docker compose ps
```

Expected health response:

```json
{"status":"ok"}
```

Open:

- Application: `http://localhost:3000`
- API documentation: `http://localhost:8000/docs`

Stop the services without deleting data:

```bash
docker compose down
```

To deliberately delete the local database and recreate it from migrations:

```bash
docker compose down --volumes
docker compose up --build
```

The `--volumes` command permanently removes the local Compose database. Do not use it if the data must be retained.

## 6. Manual local setup

### API with SQLite

Create a virtual environment and install the API:

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r apps/api/requirements-local.txt
```

For a no-Postgres local run, change this line in `.env`:

```dotenv
DATABASE_URL=sqlite+pysqlite:///./mireye.sqlite3
```

Start the API:

```bash
PYTHONPATH=apps/api .venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Web application

In a second terminal:

```bash
cd apps/web
npm install
npm run dev
```

Open `http://localhost:3000`.

If you use local PostgreSQL instead of SQLite, create a PostGIS-enabled database and set a compatible `DATABASE_URL`. The full normalized production schema is created by `infrastructure/migrations/001_initial.sql`; SQLite is intended for development and automated tests.

## 7. Verify the installation

Run backend checks from the repository root:

```bash
make lint
make test
make eval
```

Run the frontend production checks:

```bash
cd apps/web
npm run lint
npm run build
npm audit --audit-level=high
```

The evaluation report is written to `evaluation/reports/latest.json`, with failures in `evaluation/reports/failures.json`.

## 8. First investigation

1. Open `http://localhost:3000/profile` and create a buyer profile.
2. Return to the home page.
3. Select address, listing URL, or natural-language query.
4. Enter a resolvable agricultural property, such as an address or a query containing `near City, ST`.
5. Select the buyer profile and start the investigation.
6. Review the live timeline, claim transitions, evidence provenance, valuation, strategy, and dossier.

Without a market provider, valuation will remain unavailable. Without Mireye, the run still attempts USDA and configured market investigations and records the missing Mireye context. Without OpenAI, deterministic fallback investigation candidates still run, but specialist/critic model assessments are unavailable.

## 9. Common problems

### Cannot connect to the Docker daemon

Start Docker Desktop, wait until its engine reports that it is running, and retry:

```bash
docker info
docker compose up --build
```

### API starts but the web app cannot reach it

Check:

```dotenv
NEXT_PUBLIC_API_URL=http://localhost:8000
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

Then restart/rebuild the web app because `NEXT_PUBLIC_*` values are embedded into the frontend build.

### API returns 401

`APP_API_KEY` is set. Either leave it blank for local browser development or include its bearer token in API requests.

### Investigation completes without valuation

Configure `NASS_QUICKSTATS_API_KEY` (or the custom `MARKET_BENCHMARK_URL`) and
preferably `MARKET_COMPARABLES_URL`. The application intentionally refuses to invent
market values. USDA provides a benchmark but not transaction-level comparables.

### Mireye is shown as unavailable

Verify REST authentication without starting an investigation:

```bash
curl -i -H "Authorization: Bearer $MIREYE_API_TOKEN" \
  "$MIREYE_API_URL/v1/meta/fields"
```

For MCP, verify that the URL ends in `/mcp`; `https://api.mireye.com` by itself
is not the MCP endpoint. Restart the API after changing `.env`.

### OpenAI assessments do not appear

Confirm that `OPENAI_API_KEY` is in the root `.env`, the API process was restarted after editing it, the project has API billing/credits, and the selected model is available to the project. Provider exceptions are deliberately converted into safe `None` results, so inspect API logs and the investigation limitations/trace.

### Database schema changes are not appearing in Docker

Postgres initialization scripts run only for a new volume. Back up important data, then explicitly recreate the development volume, or apply the migration through your production migration process.

## 10. Production checklist

Before a real deployment:

- replace the development Postgres username and password;
- use a managed PostgreSQL/PostGIS database with backups;
- terminate HTTPS at a load balancer or reverse proxy;
- use an identity-aware gateway or server-side user sessions;
- store provider secrets in a secrets manager, not an image or repository;
- restrict CORS to the deployed web origin;
- configure provider timeouts, quotas, and spend alerts;
- use licensed market data appropriate for the intended decision;
- validate Mireye schemas and market contracts in a staging environment;
- run `make lint`, `make test`, `make eval`, and the frontend production build;
- monitor request IDs, provider limitations, tool latency, and failed investigations;
- preserve the disclaimer that physical/raster evidence is not a survey, legal parcel boundary, appraisal, water-right determination, or substitute for transaction diligence.
