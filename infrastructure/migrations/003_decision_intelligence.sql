CREATE TABLE IF NOT EXISTS property_boundaries (
  investigation_id uuid PRIMARY KEY REFERENCES investigations(id),
  boundary_kind text NOT NULL,
  geometry geography(Geometry, 4326) NOT NULL,
  area_acres numeric NOT NULL,
  source_name text NOT NULL,
  payload jsonb NOT NULL,
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS financial_inputs (
  investigation_id uuid PRIMARY KEY REFERENCES investigations(id),
  payload jsonb NOT NULL,
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS investment_decisions (
  investigation_id uuid PRIMARY KEY REFERENCES investigations(id),
  verdict text NOT NULL,
  maximum_defensible_offer numeric,
  payload jsonb NOT NULL,
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS cash_flow_scenarios (
  id uuid PRIMARY KEY,
  investigation_id uuid NOT NULL REFERENCES investigations(id),
  scenario_name text NOT NULL,
  activity text NOT NULL,
  payload jsonb NOT NULL
);

CREATE TABLE IF NOT EXISTS hazard_observations (
  id uuid PRIMARY KEY,
  investigation_id uuid NOT NULL REFERENCES investigations(id),
  hazard text NOT NULL,
  geometry geography(Geometry, 4326),
  source_vintage text,
  payload jsonb NOT NULL
);

CREATE TABLE IF NOT EXISTS listing_candidates (
  id uuid PRIMARY KEY,
  investigation_id uuid NOT NULL REFERENCES investigations(id),
  provider_listing_id text,
  canonical_url text,
  location geography(Point, 4326),
  investigation_depth text NOT NULL,
  payload jsonb NOT NULL
);

CREATE INDEX IF NOT EXISTS hazard_observations_investigation_idx
  ON hazard_observations(investigation_id);
CREATE INDEX IF NOT EXISTS listing_candidates_investigation_idx
  ON listing_candidates(investigation_id);
