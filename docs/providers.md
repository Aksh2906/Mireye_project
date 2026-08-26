# Provider configuration

## Mireye MCP

Set `MIREYE_MCP_URL` and, when required, `MIREYE_MCP_TOKEN`. The adapter uses MCP JSON-RPC tool discovery before invocation and stores exact tool arguments and results as evidence references. Provider-specific tool names are mapped at the adapter boundary.

## OpenAI

Set `OPENAI_API_KEY`, `OPENAI_MODEL`, and `OPENAI_REASONING_EFFORT`. OpenAI is called only by the isolated agent runtime. The default is the current flagship agentic model, while deployment can select another supported model. Application calculations and rendering do not use the model.

Set `APP_API_KEY` to require a bearer token on all `/api/*` endpoints. It is optional for local development and should be configured at the ingress or API layer in deployment.

## USDA

CDL and SSURGO endpoints are configurable. Evidence records preserve publisher, dataset, URL, retrieval time, vintage, resolution, and limitations. CDL is a historical raster proxy and is never represented as a surveyed or legal acreage measurement.

CropScape `GetCDLValue` receives coordinates transformed from WGS84 to its documented CONUS Albers CRS (EPSG:5070). SSURGO uses its documented WGS84 mapunit-intersection function and REST/POST query contract.

## Market data

Set `NASS_QUICKSTATS_API_KEY` to use the built-in USDA NASS state farm-real-estate
value-per-acre benchmark. `MARKET_BENCHMARK_URL` optionally overrides NASS with a
service implementing the documented benchmark adapter response.
`MARKET_COMPARABLES_URL` remains a separate service returning provenance-bearing
transactions; Quick Stats does not provide property-sale comparables. When absent,
valuation remains unavailable or broad rather than inventing a market value. Each
comparable must include sale price and acreage; price per acre is calculated
deterministically.
