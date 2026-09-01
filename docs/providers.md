# Provider configuration

## Mireye

Set `MIREYE_API_URL=https://api.mireye.com` and `MIREYE_API_TOKEN`. The primary hazard and alternative-use workflows call REST `/v1/fetch` with catalog-backed fields and retain field-level provenance and failures. `/v1/ask` is reserved for narrative context and uses a 120-second client timeout. MCP remains a fallback when `MIREYE_API_URL` is blank; set `MIREYE_MCP_URL` and `MIREYE_MCP_TOKEN` for runtime JSON-RPC tool discovery.

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

## Crop and activity economics

Set `AGRICULTURE_ECONOMICS_URL` and optional `AGRICULTURE_ECONOMICS_TOKEN` for a maintained enterprise-budget service. The adapter accepts both per-acre crop assumptions and productive-unit models for dairy/livestock. Every yield/production, price, cost, infrastructure, and quantity observation retains publisher, dataset, vintage, geography, confidence, units, and limitations. Incomplete assumptions produce `insufficient evidence`, not a profitability claim.

## Listing discovery and boundaries

`GenericListingUrlAdapter` supports user-provided public URLs. `MockListingAdapter` supports reviewed fixtures. The default `LISTING_SEARCH_URL=https://api.rentcast.io/v1/listings/sale` uses the dedicated RentCast adapter and requires its API key in `LISTING_API_TOKEN`. Search requests active `Land` records, is adaptive, deduplicates candidates, applies budget/acreage/distance filters, and deep-analyzes shortlisted results. RentCast rural-land coverage is not complete; replace it with a licensed local MLS/RESO or rural-land feed where needed. LandWatch and Land.com remain unavailable placeholders because the application does not scrape around terms, robots rules, rate limits, or access controls.

Set `PARCEL_API_URL` and optional `PARCEL_API_TOKEN` for a permitted parcel endpoint accepting `latitude` and `longitude` query parameters and returning GeoJSON geometry plus source metadata. Boundary priority is exact listing geometry, authoritative parcel geometry, user-provided polygon, then explicitly labeled analysis geometry. Polygon area is calculated geodesically and compared with claimed acreage, but no geometry is represented as a legal survey or ownership determination.

## Disaster and hazard context

Mireye `/v1/fetch` is the primary disaster/hazard source. It requests FEMA flood/floodplain, wetlands, wildfire, wind, hail, tornado, lightning, landslide, shrink-swell, fire-zone, burn-probability, and seismic/design-wind fields. `HAZARD_API_URL` and optional `HAZARD_API_TOKEN` are an optional supplemental provider for fields not returned by Mireye. Missing provider data remains unknown; it is never displayed as no risk.

Hazard observations are translated into activity-specific consequences, mitigation/diligence actions, and explicit conservative scenario stresses. The application does not hide disaster exposure inside an opaque property score.
