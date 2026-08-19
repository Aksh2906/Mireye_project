CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS buyer_profiles (
  id uuid PRIMARY KEY,
  payload jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS investigations (
  id uuid PRIMARY KEY,
  status text NOT NULL,
  input_type text NOT NULL,
  raw_input text NOT NULL,
  payload jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS investigations_status_idx ON investigations(status);
CREATE TABLE IF NOT EXISTS users (
  id uuid PRIMARY KEY, email text UNIQUE NOT NULL, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS buyer_profile_preferences (
  id uuid PRIMARY KEY, buyer_profile_id uuid NOT NULL REFERENCES buyer_profiles(id),
  preference_key text NOT NULL, preference_value jsonb NOT NULL
);
CREATE TABLE IF NOT EXISTS properties (
  id uuid PRIMARY KEY, address text, location geography(Point, 4326), acreage numeric,
  parcel_identifier text, payload jsonb NOT NULL
);
CREATE TABLE IF NOT EXISTS investigation_inputs (
  id uuid PRIMARY KEY, investigation_id uuid NOT NULL REFERENCES investigations(id),
  input_type text NOT NULL, raw_input text NOT NULL, payload jsonb NOT NULL
);
CREATE TABLE IF NOT EXISTS investigation_runs (
  id uuid PRIMARY KEY, investigation_id uuid NOT NULL REFERENCES investigations(id),
  status text NOT NULL, started_at timestamptz NOT NULL, completed_at timestamptz
);
CREATE TABLE IF NOT EXISTS claims (
  id uuid PRIMARY KEY, investigation_id uuid NOT NULL REFERENCES investigations(id),
  claim_type text NOT NULL, claim_text text NOT NULL, state text NOT NULL,
  materiality text, source_id text NOT NULL, payload jsonb NOT NULL
);
CREATE TABLE IF NOT EXISTS claim_state_transitions (
  id uuid PRIMARY KEY, claim_id uuid NOT NULL REFERENCES claims(id),
  from_state text NOT NULL, to_state text NOT NULL, confidence numeric NOT NULL,
  rationale text NOT NULL, evidence_ids jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS evidence_sources (
  id uuid PRIMARY KEY, source_type text NOT NULL, publisher text NOT NULL, dataset text NOT NULL,
  source_url text, vintage text, retrieved_at timestamptz NOT NULL, payload jsonb NOT NULL
);
CREATE TABLE IF NOT EXISTS evidence (
  id uuid PRIMARY KEY, investigation_id uuid NOT NULL REFERENCES investigations(id),
  source_type text NOT NULL, field_name text NOT NULL, geometry geometry,
  retrieved_at timestamptz NOT NULL, payload jsonb NOT NULL
);
CREATE TABLE IF NOT EXISTS evidence_relationships (
  id uuid PRIMARY KEY, investigation_id uuid NOT NULL REFERENCES investigations(id),
  source_id uuid NOT NULL, target_id uuid NOT NULL, relationship text NOT NULL
);
CREATE TABLE IF NOT EXISTS agent_runs (
  id uuid PRIMARY KEY, investigation_id uuid NOT NULL REFERENCES investigations(id),
  agent_name text NOT NULL, status text NOT NULL, started_at timestamptz NOT NULL,
  completed_at timestamptz, input_state_hash text, output_summary text, error text
);
CREATE TABLE IF NOT EXISTS tool_calls (
  id uuid PRIMARY KEY, investigation_id uuid NOT NULL REFERENCES investigations(id),
  agent_run_id uuid REFERENCES agent_runs(id), tool_name text NOT NULL,
  status text NOT NULL, latency_ms integer, cost numeric, payload jsonb NOT NULL
);
CREATE TABLE IF NOT EXISTS derived_signals (
  id uuid PRIMARY KEY, investigation_id uuid NOT NULL REFERENCES investigations(id),
  name text NOT NULL, materiality text NOT NULL, payload jsonb NOT NULL
);
CREATE TABLE IF NOT EXISTS contradictions (
  id uuid PRIMARY KEY, investigation_id uuid NOT NULL REFERENCES investigations(id),
  claim_id uuid REFERENCES claims(id), materiality text NOT NULL, payload jsonb NOT NULL
);
CREATE TABLE IF NOT EXISTS unknowns (
  id uuid PRIMARY KEY, investigation_id uuid NOT NULL REFERENCES investigations(id),
  question text NOT NULL, materiality text NOT NULL, payload jsonb NOT NULL
);
CREATE TABLE IF NOT EXISTS valuations (
  id uuid PRIMARY KEY, investigation_id uuid NOT NULL REFERENCES investigations(id),
  estimated_value numeric, low_value numeric, high_value numeric, confidence numeric,
  payload jsonb NOT NULL
);
CREATE TABLE IF NOT EXISTS valuation_factors (
  id uuid PRIMARY KEY, valuation_id uuid NOT NULL REFERENCES valuations(id),
  factor_name text NOT NULL, adjustment numeric, evidence_ids jsonb NOT NULL, payload jsonb NOT NULL
);
CREATE TABLE IF NOT EXISTS comparables (
  id uuid PRIMARY KEY, valuation_id uuid NOT NULL REFERENCES valuations(id),
  source_url text, sale_price numeric, acreage numeric, payload jsonb NOT NULL
);
CREATE TABLE IF NOT EXISTS decisions (
  id uuid PRIMARY KEY, investigation_id uuid NOT NULL REFERENCES investigations(id),
  verdict text NOT NULL, confidence numeric NOT NULL, payload jsonb NOT NULL
);
CREATE TABLE IF NOT EXISTS diligence_requests (
  id uuid PRIMARY KEY, investigation_id uuid NOT NULL REFERENCES investigations(id),
  priority text NOT NULL, request text NOT NULL, payload jsonb NOT NULL
);
CREATE TABLE IF NOT EXISTS negotiation_strategies (
  id uuid PRIMARY KEY, investigation_id uuid NOT NULL REFERENCES investigations(id), payload jsonb NOT NULL
);
CREATE TABLE IF NOT EXISTS reports (
  id uuid PRIMARY KEY, investigation_id uuid NOT NULL REFERENCES investigations(id),
  format text NOT NULL, payload jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now()
);
