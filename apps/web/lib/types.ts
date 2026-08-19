export interface BuyerProfile {
  id: string;
  name: string;
  target_states: string[];
  budget_max: number | null;
  minimum_acres: number | null;
  maximum_acres: number | null;
  preferred_crops: string[];
  flood_risk_tolerance: string;
  desired_land_use: string | null;
  risk_tolerance: string;
}

export interface InvestigationEvent {
  id: string;
  type: string;
  message: string;
  created_at: string;
}

export interface PropertyRecord {
  address: string | null;
  latitude: number | null;
  longitude: number | null;
  acreage: number | null;
  county: string | null;
}

export interface DecisionRecord {
  verdict: "ACQUIRE" | "DO_NOT_ACQUIRE";
  qualification: string;
  confidence: number;
  decision_summary: string;
  critical_reasons: string[];
}

export interface ClaimRecord {
  id: string;
  claim_text: string;
  claim_type: string;
  state: string;
  materiality: string | null;
}

export interface ClaimTransitionRecord {
  id: string;
  from_state: string;
  to_state: string;
  rationale: string;
  created_at: string;
}
export interface EvidenceRecord {
  id: string;
  source_type: string;
  source: { publisher: string; dataset: string; vintage: string | null };
  field_name: string;
  value: unknown;
  unit: string | null;
  confidence: number;
  semantic_scope: string | null;
  spatial_resolution: string | null;
  limitations: string[];
  geometry: Record<string, unknown> | null;
}
export interface SignalRecord {
  id: string;
  name: string;
  value: string | number | boolean | null;
  interpretation: string;
  materiality: string;
}
export interface UnknownRecord {
  id: string;
  question: string;
  materiality: string;
  resolvable: boolean;
  candidate_tools: string[];
}
export interface ComparableRecord {
  id: string;
  location: string | null;
  sale_price: number;
  acreage: number;
  price_per_acre: number;
  sale_date: string | null;
}
export interface StabilityRecord {
  stable: boolean;
  classification: string;
  explanation: string;
  downside_verdict: string;
  upside_verdict: string;
}
export interface NegotiationRecord {
  action: string;
  rationale: string;
}

export interface ContradictionRecord {
  id: string;
  description: string;
  decision_impact: string | null;
}

export interface DiligenceRecord {
  priority: string;
  request: string;
  reason: string;
}

export interface ValuationRecord {
  estimated_value_total: number | null;
  estimated_value_per_acre: number | null;
  low: number | null;
  high: number | null;
  asking_price: number | null;
  confidence: number;
  key_value_drivers: string[];
  key_downside_drivers: string[];
  limitations: string[];
}

export interface InvestigationRecord {
  id: string;
  status: string;
  raw_input: string;
  created_at: string;
  property: PropertyRecord | null;
  decision: DecisionRecord | null;
  events: InvestigationEvent[];
  claims: ClaimRecord[];
  claim_transitions: ClaimTransitionRecord[];
  evidence: EvidenceRecord[];
  signals: SignalRecord[];
  unknowns: UnknownRecord[];
  comparables: ComparableRecord[];
  decision_stability: StabilityRecord | null;
  contradictions: ContradictionRecord[];
  diligence: DiligenceRecord[];
  negotiation: NegotiationRecord[];
  valuation: ValuationRecord | null;
  limitations: string[];
}
