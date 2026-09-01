# Local setup guide

This guide runs the FastAPI service, Next.js application, and SQLite database directly on a local machine. External credentials are optional for startup. Features that depend on an unavailable provider report an explicit limitation instead of creating substitute data.

## 1. Install prerequisites

- Git
- Python 3.12
- Node.js 22 or newer
- npm
- GNU Make for automated setup

Check the commands:

```bash
git --version
python3.12 --version
node --version
npm --version
make --version
```

## 2. Clone and install

```bash
git clone https://github.com/Aksh2906/Mireye_project.git
cd Mireye_project
make setup
```

The setup script creates `.venv`, installs the Python and Node dependencies, creates a private empty `.env` when needed, and runs `make doctor`.

## 3. Configure `.env`

Environment files are intentionally excluded from Git. Add only the provider settings needed for your analysis. The complete copy-ready configuration and provider table are in `README.md`.

Minimum local configuration:

```dotenv
APP_ENV=development
DATABASE_URL=sqlite+pysqlite:///./mireye.sqlite3
NEXT_PUBLIC_API_URL=http://localhost:8000
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

Recommended provider configuration:

```dotenv
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
```

Never put server credentials in a `NEXT_PUBLIC_*` setting.

## 4. Validate and run

```bash
make doctor
make dev
```

Open:

- Application: `http://localhost:3000`
- API documentation: `http://localhost:8000/docs`
- API health: `http://localhost:8000/health`

Press `Ctrl+C` to stop the API and web processes.

To run them separately:

```bash
make api-dev
```

```bash
make web-dev
```

## 5. Manual installation

### macOS or Linux

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r apps/api/requirements-local.txt
npm install --prefix apps/web
touch .env
chmod 600 .env
```

API terminal:

```bash
PYTHONPATH=apps/api .venv/bin/python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Web terminal:

```bash
npm --prefix apps/web run dev -- --hostname 127.0.0.1
```

### Windows PowerShell

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r apps/api/requirements-local.txt
npm install --prefix apps/web
New-Item -Path .env -ItemType File -Force
```

API terminal:

```powershell
$env:PYTHONPATH="apps/api"
.venv\Scripts\python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Web terminal:

```powershell
npm --prefix apps/web run dev -- --hostname 127.0.0.1
```

## 6. Verify the project

```bash
make lint
make test
make eval
```

```bash
cd apps/web
npm run lint
npm run build
```

## 7. Provider checks

Test Mireye catalog access after exporting the local variables into your terminal session:

```bash
curl -i -H "Authorization: Bearer $MIREYE_API_TOKEN" "$MIREYE_API_URL/v1/meta/fields"
```

The RentCast adapter expects:

```dotenv
LISTING_SEARCH_URL=https://api.rentcast.io/v1/listings/sale
LISTING_API_TOKEN=your_local_key
```

The credential is sent as `X-Api-Key`. Provider connection failures become an unavailable listing result and do not terminate the main investigation.

## 8. Troubleshooting

### Missing Python command

The automated script requires `python3.12`. Install Python 3.12 and ensure that command is available in the same terminal.

### Missing `.env`

Run `make setup`, or create the root `.env` manually. The file must remain untracked.

### Web application cannot call the API

Confirm:

```dotenv
NEXT_PUBLIC_API_URL=http://localhost:8000
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

Restart the web application after changing a `NEXT_PUBLIC_*` setting.

### API returns 401

Leave `APP_API_KEY` blank for ordinary local UI development. If it is configured, clients must send its value as a bearer token.

### Mireye fields are unavailable

Check the hosted base URL, bearer token, `/v1/meta/fields` response, and network access. The MCP URL must end with `/mcp` when that fallback is enabled.

### Valuation or ROI is unavailable

Configure a market benchmark and sourced economic inputs, or add traceable assumptions on the Economics page. The calculation engines require production or yield, commodity price, and operating costs.

### Boundary analysis is unavailable

Provide listing geometry, configure a parcel provider, upload or draw a valid polygon, or allow the application to create an explicitly labeled analysis shape. A polygon exterior ring requires at least three distinct points and a closed ring.

## 9. Production preparation

- Use a managed PostgreSQL/PostGIS database with backups when durable multi-user storage is required.
- Apply the SQL files in `infrastructure/migrations` through the database migration process.
- Store credentials in an approved secrets manager.
- Add an identity-aware gateway or server-side session layer.
- Restrict CORS to the deployed web origin.
- Configure provider timeouts, quotas, monitoring, and spend alerts.
- Validate provider schemas in a staging environment.
- Run the complete verification suite before release.
