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
  geometry?: { type: string; coordinates: unknown } | null;
}

export interface DecisionRecord {
  verdict:
    | "ACQUIRE"
    | "ACQUIRE_CONDITIONALLY"
    | "NEGOTIATE"
    | "DO_NOT_ACQUIRE"
    | "INSUFFICIENT_EVIDENCE";
  qualification: string;
  confidence: number;
  decision_summary: string;
  critical_reasons: string[];
}
export interface BuyerObjectiveRecord {
  objective: string;
  risk_tolerance: string;
  agricultural_activities: string[];
  infrastructure_investment_budget: number | null;
  willingness_to_pay_premium: boolean;
}
export interface HypothesisRecord {
  id: string;
  statement: string;
  status: string;
  importance: string;
  confidence: number;
}
export interface EconomicScenarioRecord {
  name: string;
  activity: string;
  annual_revenue: number | null;
  annual_operating_cost: number | null;
  annual_operating_profit: number | null;
  total_investment: number | null;
  roi: number | null;
  payback_years: number | null;
  confidence: number;
  limitations: string[];
  cash_on_cash_return: number | null;
  npv: number | null;
  irr: number | null;
  debt_service_coverage_ratio: number | null;
  break_even_yield?: number | null;
  break_even_price?: number | null;
  break_even_acquisition_price?: number | null;
  key_sensitivities?: string[];
  assumptions?: Array<{
    name: string;
    value: number;
    unit: string;
    source: string;
    source_date: string | null;
    geography: string | null;
    confidence: number;
  }>;
  cash_flows: Array<{
    year: number;
    revenue: number;
    operating_cost: number;
    debt_service: number;
    capital_cost: number;
    net_cash_flow: number;
  }>;
}
export interface CropOpportunityRecord {
  crop: string;
  physical_fit: string;
  historical_support: string;
  economic_scenarios: EconomicScenarioRecord[];
  infrastructure_needs: string[];
  major_risks: string[];
  confidence: number;
  recommendation: string;
}
export interface ActivityOpportunityRecord {
  activity: string;
  fit: string;
  rationale: string[];
  economic_scenarios: EconomicScenarioRecord[];
  infrastructure_needs: string[];
  risks: string[];
  confidence: number;
}
export interface HazardAssessmentRecord {
  hazard: string;
  exposure: string;
  relevant_activities: string[];
  agricultural_consequences: string[];
  materiality: string;
  confidence: number;
  source_name: string | null;
  source_vintage: string | null;
  geometry: Record<string, unknown> | null;
  affected_area_acres: number | null;
  mitigation_actions: string[];
  annual_profit_stress: number;
}
export interface AlternativeRecord {
  id: string;
  title: string | null;
  price: number | null;
  acreage: number | null;
  advantages: string[];
  disadvantages: string[];
  unknowns: string[];
  evidence_quality: number;
  investigation_depth: string;
  location: { type: string; coordinates: number[] };
  source_url: string | null;
  distance_miles: number | null;
  price_per_acre: number | null;
  comparison_delta: number | null;
  recommendation: string;
  economic_scenarios: EconomicScenarioRecord[];
}

export interface BoundaryRecord {
  geometry: { type: string; coordinates: unknown };
  kind: string;
  source_name: string;
  source_url: string | null;
  retrieved_at: string;
  confidence: number;
  area_acres: number;
  claimed_acres: number | null;
  acreage_difference: number | null;
  acreage_difference_percent: number | null;
  is_legal_boundary: boolean;
  limitations: string[];
}

export interface FinancialInputsRecord {
  down_payment_percent: number;
  interest_rate: number;
  loan_term_years: number;
  closing_cost_percent: number;
  annual_property_tax: number;
  annual_insurance: number;
  annual_owner_labor: number;
  working_capital: number;
  initial_capex: number;
  annual_replacement_capex: number;
  discount_rate: number;
  time_horizon_years: number;
  residual_value: number | null;
  annual_land_appreciation: number;
  assumptions_source: string;
}

export interface InvestmentDecisionRecord {
  verdict: string;
  label: string;
  rationale: string[];
  maximum_defensible_offer: number | null;
  base_case_roi: number | null;
  base_case_npv: number | null;
  base_case_irr: number | null;
  downside_roi: number | null;
  evidence_confidence: number;
  material_unknowns: string[];
  limitations: string[];
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
  source: {
    publisher: string;
    dataset: string;
    vintage: string | null;
    url?: string | null;
    retrieved_at?: string;
  };
  field_name: string;
  value: unknown;
  unit: string | null;
  confidence: number;
  semantic_scope: string | null;
  spatial_resolution: string | null;
  limitations: string[];
  geometry: Record<string, unknown> | null;
  temporal_resolution?: string | null;
  raw_reference?: Record<string, unknown>;
}
export interface SignalRecord {
  id: string;
  name: string;
  value: string | number | boolean | null;
  interpretation: string;
  materiality: string;
  confidence?: number;
  method?: string;
  limitations?: string[];
  applicable_objectives?: string[];
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
  user_objective: BuyerObjectiveRecord;
  hypotheses: HypothesisRecord[];
  iteration: number;
  termination_reason: string | null;
  crop_opportunities: CropOpportunityRecord[];
  activity_opportunities: ActivityOpportunityRecord[];
  economic_scenarios: EconomicScenarioRecord[];
  hazard_assessments: HazardAssessmentRecord[];
  alternatives: AlternativeRecord[];
  boundary: BoundaryRecord | null;
  financial_inputs: FinancialInputsRecord;
  investment_decision: InvestmentDecisionRecord | null;
  searched_radii_miles: number[];
}
