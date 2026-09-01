CREATE TABLE IF NOT EXISTS buyer_objectives (
  id uuid PRIMARY KEY, investigation_id uuid NOT NULL REFERENCES investigations(id),
  payload jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS hypotheses (
  id uuid PRIMARY KEY, investigation_id uuid NOT NULL REFERENCES investigations(id),
  status text NOT NULL, importance text NOT NULL, payload jsonb NOT NULL
);
CREATE TABLE IF NOT EXISTS investigation_actions (
  id uuid PRIMARY KEY, investigation_id uuid NOT NULL REFERENCES investigations(id),
  action_type text NOT NULL, target text NOT NULL, status text NOT NULL,
  expected_decision_impact numeric, estimated_cost numeric, actual_cost numeric,
  payload jsonb NOT NULL
);
CREATE TABLE IF NOT EXISTS economic_scenarios (
  id uuid PRIMARY KEY, investigation_id uuid NOT NULL REFERENCES investigations(id),
  scenario_name text NOT NULL, activity text NOT NULL, payload jsonb NOT NULL
);
CREATE TABLE IF NOT EXISTS agricultural_opportunities (
  id uuid PRIMARY KEY, investigation_id uuid NOT NULL REFERENCES investigations(id),
  activity text NOT NULL, payload jsonb NOT NULL
);
CREATE TABLE IF NOT EXISTS hazard_assessments (
  id uuid PRIMARY KEY, investigation_id uuid NOT NULL REFERENCES investigations(id),
  hazard text NOT NULL, materiality text NOT NULL, payload jsonb NOT NULL
);
CREATE TABLE IF NOT EXISTS property_alternatives (
  id uuid PRIMARY KEY, investigation_id uuid NOT NULL REFERENCES investigations(id),
  investigation_depth text NOT NULL, location geography(Point, 4326), payload jsonb NOT NULL
);
CREATE INDEX IF NOT EXISTS hypotheses_investigation_idx ON hypotheses(investigation_id);
CREATE INDEX IF NOT EXISTS actions_investigation_idx ON investigation_actions(investigation_id);
CREATE INDEX IF NOT EXISTS alternatives_investigation_idx ON property_alternatives(investigation_id);
