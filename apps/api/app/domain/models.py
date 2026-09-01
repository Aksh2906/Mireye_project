from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, HttpUrl, model_validator


def utcnow() -> datetime:
    return datetime.now(UTC)


class InputType(StrEnum):
    ADDRESS = "address"
    LISTING_URL = "listing_url"
    QUERY = "query"
    LOCATION = "location"


class InvestigationStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    NEEDS_INPUT = "needs_input"


class ClaimState(StrEnum):
    UNKNOWN = "UNKNOWN"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    UNDER_INVESTIGATION = "UNDER_INVESTIGATION"
    SUPPORTED = "SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    NOT_MATERIAL = "NOT_MATERIAL"


class SourceType(StrEnum):
    MIREYE = "MIREYE"
    USDA_CDL = "USDA_CDL"
    USDA_SSURGO = "USDA_SSURGO"
    USDA_AG_STATISTICS = "USDA_AG_STATISTICS"
    MARKET_DATA = "MARKET_DATA"
    LISTING = "LISTING"
    USER_PROVIDED = "USER_PROVIDED"
    GEOCODER = "GEOCODER"
    PARCEL = "PARCEL"
    HAZARD = "HAZARD"
    WEB_SOURCE = "WEB_SOURCE"
    DERIVED = "DERIVED"


class Materiality(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class Verdict(StrEnum):
    ACQUIRE = "ACQUIRE"
    ACQUIRE_CONDITIONALLY = "ACQUIRE_CONDITIONALLY"
    NEGOTIATE = "NEGOTIATE"
    DO_NOT_ACQUIRE = "DO_NOT_ACQUIRE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class ObjectiveType(StrEnum):
    MAXIMIZE_PROFIT = "maximize_profit"
    MINIMIZE_RISK = "minimize_risk"
    BALANCED = "balanced"
    LIVESTOCK = "livestock"
    CROP = "crop"
    DAIRY = "dairy"
    GRAZING = "grazing"
    INVESTMENT = "investment"
    CUSTOM = "custom"


class RiskTolerance(StrEnum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class ActivityCategory(StrEnum):
    ROW_CROP = "row_crop"
    GRAZING = "grazing"
    CATTLE = "cattle"
    DAIRY = "dairy"
    SHEEP = "sheep"
    GOAT = "goat"
    HAY = "hay"
    ORCHARD = "orchard"
    GREENHOUSE = "greenhouse"
    SOLAR = "solar"
    WIND = "wind"
    MIXED = "mixed"


class BoundaryKind(StrEnum):
    LISTING = "listing_geometry"
    AUTHORITATIVE_PARCEL = "authoritative_parcel"
    USER_UPLOADED = "user_uploaded"
    USER_DRAWN = "user_drawn"
    ANALYSIS = "analysis_geometry"


class Geometry(BaseModel):
    type: str = "Point"
    coordinates: Any = Field(default_factory=list)


class BoundaryRecord(BaseModel):
    geometry: Geometry
    kind: BoundaryKind
    source_name: str
    source_url: str | None = None
    retrieved_at: datetime = Field(default_factory=utcnow)
    confidence: float = Field(default=0.5, ge=0, le=1)
    area_acres: float = Field(ge=0)
    claimed_acres: float | None = Field(default=None, gt=0)
    acreage_difference: float | None = None
    acreage_difference_percent: float | None = None
    is_legal_boundary: bool = False
    limitations: list[str] = Field(default_factory=list)


class BuyerBudget(BaseModel):
    acquisition_max: float | None = Field(default=None, gt=0)
    total_investment_max: float | None = Field(default=None, gt=0)


class AcreagePreference(BaseModel):
    minimum: float | None = Field(default=None, gt=0)
    maximum: float | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_range(self):
        if self.minimum and self.maximum and self.minimum > self.maximum:
            raise ValueError("minimum acreage cannot exceed maximum acreage")
        return self


class GeographyPreference(BaseModel):
    origin: Geometry | None = None
    max_distance_miles: float | None = Field(default=None, gt=0)
    preferred_regions: list[str] = Field(default_factory=list)


class BuyerObjective(BaseModel):
    budget: BuyerBudget = Field(default_factory=BuyerBudget)
    acreage: AcreagePreference = Field(default_factory=AcreagePreference)
    geography: GeographyPreference = Field(default_factory=GeographyPreference)
    objective: ObjectiveType = ObjectiveType.BALANCED
    agricultural_activities: list[ActivityCategory] = Field(default_factory=list)
    return_target: float | None = None
    payback_target_years: float | None = Field(default=None, gt=0)
    risk_tolerance: RiskTolerance = RiskTolerance.MODERATE
    infrastructure_investment_budget: float | None = Field(default=None, ge=0)
    time_horizon_years: int | None = Field(default=None, gt=0)
    willingness_to_pay_premium: bool = False
    constraints: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def normalize_activity_intent(self):
        implied = {
            ObjectiveType.CROP: ActivityCategory.ROW_CROP,
            ObjectiveType.GRAZING: ActivityCategory.GRAZING,
            ObjectiveType.LIVESTOCK: ActivityCategory.CATTLE,
            ObjectiveType.DAIRY: ActivityCategory.DAIRY,
        }.get(self.objective)
        if implied and implied not in self.agricultural_activities:
            self.agricultural_activities.append(implied)
        if (
            self.budget.acquisition_max
            and self.budget.total_investment_max
            and self.budget.total_investment_max < self.budget.acquisition_max
        ):
            raise ValueError("total investment budget cannot be below acquisition budget")
        return self


class Property(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    state: str | None = None
    county: str | None = None
    parcel_identifier: str | None = None
    acreage: float | None = Field(default=None, gt=0)
    geometry: Geometry | None = None


class ListingArtifact(BaseModel):
    url: str | None = None
    asking_price: float | None = Field(default=None, gt=0)
    source: str | None = None
    raw_text: str | None = None
    retrieved_at: datetime | None = None
    limitations: list[str] = Field(default_factory=list)


class BuyerProfileBase(BaseModel):
    name: str
    target_states: list[str] = Field(default_factory=list)
    target_counties: list[str] = Field(default_factory=list)
    target_regions: list[str] = Field(default_factory=list)
    minimum_acres: float | None = None
    maximum_acres: float | None = None
    budget_min: float | None = None
    budget_max: float | None = None
    preferred_crops: list[str] = Field(default_factory=list)
    irrigation_preference: str | None = None
    risk_tolerance: str = "moderate"
    investment_horizon_years: int | None = None
    desired_land_use: str | None = None
    desired_return: float | None = None
    financing_assumptions: dict[str, Any] = Field(default_factory=dict)
    flood_risk_tolerance: str = "moderate"
    soil_preferences: list[str] = Field(default_factory=list)
    access_preferences: list[str] = Field(default_factory=list)
    water_preferences: list[str] = Field(default_factory=list)
    valuation_preferences: dict[str, Any] = Field(default_factory=dict)


class BuyerProfile(BuyerProfileBase):
    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class BuyerProfileUpdate(BuyerProfileBase):
    pass


class Claim(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    claim_text: str
    claim_type: str
    source_id: str
    source_location: str | None = None
    extraction_confidence: float = Field(ge=0, le=1)
    state: ClaimState = ClaimState.UNKNOWN
    materiality: Materiality | None = None
    created_at: datetime = Field(default_factory=utcnow)


class ClaimStateTransition(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    claim_id: UUID
    from_state: ClaimState
    to_state: ClaimState
    evidence_ids: list[UUID]
    confidence: float = Field(ge=0, le=1)
    rationale: str
    created_at: datetime = Field(default_factory=utcnow)


class EvidenceSource(BaseModel):
    publisher: str
    dataset: str
    url: str | None = None
    retrieved_at: datetime = Field(default_factory=utcnow)
    vintage: str | None = None


class Evidence(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    source_type: SourceType
    source: EvidenceSource
    field_name: str
    value: Any
    unit: str | None = None
    geometry: dict[str, Any] | None = None
    spatial_resolution: str | None = None
    temporal_resolution: str | None = None
    semantic_scope: str | None = None
    confidence: float = Field(default=0.5, ge=0, le=1)
    limitations: list[str] = Field(default_factory=list)
    raw_reference: dict[str, Any] = Field(default_factory=dict)


class DerivedSignal(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    value: float | str | bool | None
    interpretation: str
    materiality: Materiality
    evidence_ids: list[UUID]
    method: str
    limitations: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0, le=1)
    applicable_objectives: list[str] = Field(default_factory=list)


class HypothesisStatus(StrEnum):
    UNVERIFIED = "unverified"
    SUPPORTED = "supported"
    PARTIALLY_SUPPORTED = "partially_supported"
    CONTRADICTED = "contradicted"
    UNDETERMINED = "undetermined"


class Hypothesis(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    statement: str
    status: HypothesisStatus = HypothesisStatus.UNVERIFIED
    importance: str = Field(default="medium", pattern="^(low|medium|high)$")
    supporting_evidence_ids: list[UUID] = Field(default_factory=list)
    conflicting_evidence_ids: list[UUID] = Field(default_factory=list)
    confidence: float = Field(default=0, ge=0, le=1)
    materiality: float | None = Field(default=None, ge=0, le=1)


class InvestigationAction(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    type: str
    target: str
    expected_information_gain: float = Field(ge=0, le=1)
    expected_decision_impact: float = Field(ge=0, le=1)
    estimated_cost: float = Field(ge=0)
    estimated_latency: float = Field(default=0, ge=0)
    prerequisites: list[str] = Field(default_factory=list)
    reason: str
    voi: float | None = None


class ExecutedAction(BaseModel):
    action_id: UUID
    tool_name: str
    status: str
    actual_cost: float = 0
    evidence_ids: list[UUID] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=utcnow)
    completed_at: datetime | None = None


class ToolCost(BaseModel):
    tool: str
    estimated: float
    actual: float | None = None


class InvestigationBudget(BaseModel):
    max_credits: float | None = None
    estimated_used: float = 0
    tool_costs: list[ToolCost] = Field(default_factory=list)
    remaining: float | None = None


class EconomicAssumption(BaseModel):
    name: str
    value: float
    unit: str
    source: str
    source_date: str | None = None
    geography: str | None = None
    confidence: float = Field(default=0.5, ge=0, le=1)
    scenario_classification: str = "base"


class EconomicScenario(BaseModel):
    name: str = Field(pattern="^(conservative|base|optimistic)$")
    activity: str
    annual_revenue: float | None = None
    annual_operating_cost: float | None = None
    annual_operating_profit: float | None = None
    total_investment: float | None = None
    roi: float | None = None
    payback_years: float | None = None
    break_even_yield: float | None = None
    break_even_price: float | None = None
    break_even_acquisition_price: float | None = None
    key_sensitivities: list[str] = Field(default_factory=list)
    assumptions: list[EconomicAssumption] = Field(default_factory=list)
    confidence: float = Field(default=0, ge=0, le=1)
    limitations: list[str] = Field(default_factory=list)
    cash_on_cash_return: float | None = None
    npv: float | None = None
    irr: float | None = None
    debt_service_coverage_ratio: float | None = None
    cash_flows: list[CashFlowYear] = Field(default_factory=list)


class FinancialInputs(BaseModel):
    down_payment_percent: float = Field(default=0.25, ge=0, le=1)
    interest_rate: float = Field(default=0.07, ge=0, le=1)
    loan_term_years: int = Field(default=20, gt=0, le=50)
    closing_cost_percent: float = Field(default=0.03, ge=0, le=0.25)
    annual_property_tax: float = Field(default=0, ge=0)
    annual_insurance: float = Field(default=0, ge=0)
    annual_owner_labor: float = Field(default=0, ge=0)
    working_capital: float = Field(default=0, ge=0)
    initial_capex: float = Field(default=0, ge=0)
    annual_replacement_capex: float = Field(default=0, ge=0)
    discount_rate: float = Field(default=0.08, ge=0, le=1)
    time_horizon_years: int = Field(default=10, gt=0, le=50)
    residual_value: float | None = Field(default=None, ge=0)
    annual_land_appreciation: float = Field(default=0, ge=-0.5, le=0.5)
    assumptions_source: str = "user supplied or editable planning assumptions"


class CashFlowYear(BaseModel):
    year: int = Field(ge=0)
    revenue: float = 0
    operating_cost: float = 0
    debt_service: float = 0
    capital_cost: float = 0
    net_cash_flow: float = 0


class InvestmentDecision(BaseModel):
    verdict: Verdict
    label: str
    rationale: list[str] = Field(default_factory=list)
    maximum_defensible_offer: float | None = None
    base_case_roi: float | None = None
    base_case_npv: float | None = None
    base_case_irr: float | None = None
    downside_roi: float | None = None
    evidence_confidence: float = Field(default=0, ge=0, le=1)
    material_unknowns: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class CropOpportunity(BaseModel):
    crop: str
    physical_fit: str = "unknown"
    historical_support: str = "unknown"
    economic_scenarios: list[EconomicScenario] = Field(default_factory=list)
    infrastructure_needs: list[str] = Field(default_factory=list)
    major_risks: list[str] = Field(default_factory=list)
    evidence_ids: list[UUID] = Field(default_factory=list)
    confidence: float = Field(default=0, ge=0, le=1)
    recommendation: str = "insufficient_evidence"


class AgriculturalActivityOpportunity(BaseModel):
    activity: ActivityCategory
    fit: str = "unknown"
    rationale: list[str] = Field(default_factory=list)
    economic_scenarios: list[EconomicScenario] = Field(default_factory=list)
    infrastructure_needs: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    evidence_ids: list[UUID] = Field(default_factory=list)
    confidence: float = Field(default=0, ge=0, le=1)


class ActivityRequirement(BaseModel):
    name: str
    description: str
    materiality: Materiality = Materiality.MEDIUM


class AgriculturalActivity(BaseModel):
    id: str
    category: ActivityCategory
    requirements: list[ActivityRequirement] = Field(default_factory=list)
    economics_model: str
    risk_model: str


class HazardAssessment(BaseModel):
    hazard: str
    exposure: str
    relevant_activities: list[str] = Field(default_factory=list)
    agricultural_consequences: list[str] = Field(default_factory=list)
    materiality: Materiality
    evidence_ids: list[UUID] = Field(default_factory=list)
    confidence: float = Field(default=0, ge=0, le=1)
    limitations: list[str] = Field(default_factory=list)
    source_name: str | None = None
    source_vintage: str | None = None
    geometry: dict[str, Any] | None = None
    affected_area_acres: float | None = Field(default=None, ge=0)
    mitigation_actions: list[str] = Field(default_factory=list)
    annual_profit_stress: float = Field(default=0, ge=0, le=1)


class PropertyAlternative(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    source_listing_id: str | None = None
    title: str | None = None
    location: Geometry
    price: float | None = None
    acreage: float | None = None
    relevant_signal_ids: list[UUID] = Field(default_factory=list)
    economic_scenarios: list[EconomicScenario] = Field(default_factory=list)
    advantages: list[str] = Field(default_factory=list)
    disadvantages: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    evidence_quality: float = Field(default=0, ge=0, le=1)
    investigation_depth: str = "screened"
    source_url: str | None = None
    distance_miles: float | None = Field(default=None, ge=0)
    price_per_acre: float | None = Field(default=None, ge=0)
    comparison_delta: float | None = None
    recommendation: str = "investigate"


class Contradiction(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    claim_id: UUID
    evidence_ids: list[UUID]
    description: str
    difference_type: str = "discrepancy"
    materiality: Materiality = Materiality.LOW
    decision_impact: str | None = None
    resolution_notes: list[str] = Field(default_factory=list)


class Unknown(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    question: str
    materiality: Materiality
    resolvable: bool = True
    candidate_tools: list[str] = Field(default_factory=list)


class EvidenceRelationship(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    source_id: UUID
    target_id: UUID
    relationship: str


class AgentRunArtifact(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    agent_name: str
    status: str
    started_at: datetime = Field(default_factory=utcnow)
    completed_at: datetime | None = None
    output_summary: str | None = None
    error: str | None = None


class AgentAssessment(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    agent_name: str
    assessment: str
    unknowns: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    evidence_ids: list[UUID] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)


class ToolCallArtifact(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    agent_run_id: UUID | None = None
    tool_name: str
    status: str
    started_at: datetime = Field(default_factory=utcnow)
    completed_at: datetime | None = None
    latency_ms: int | None = None
    cost: float = 0
    evidence_ids: list[UUID] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class Valuation(BaseModel):
    estimated_value_total: float | None = None
    estimated_value_per_acre: float | None = None
    low: float | None = None
    high: float | None = None
    asking_price: float | None = None
    price_gap: float | None = None
    confidence: float = Field(default=0, ge=0, le=1)
    key_value_drivers: list[str] = Field(default_factory=list)
    key_downside_drivers: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    evidence_ids: list[UUID] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class Comparable(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    source_url: str | None = None
    location: str | None = None
    sale_price: float = Field(gt=0)
    acreage: float = Field(gt=0)
    price_per_acre: float = Field(gt=0)
    sale_date: str | None = None
    adjustments: list[str] = Field(default_factory=list)
    evidence_id: UUID


class DecisionStability(BaseModel):
    stable: bool
    classification: str
    explanation: str
    downside_verdict: Verdict
    upside_verdict: Verdict


class Decision(BaseModel):
    verdict: Verdict
    qualification: str
    confidence: float = Field(ge=0, le=1)
    decision_summary: str
    critical_reasons: list[str]
    conditions: list[str] = Field(default_factory=list)
    unresolved_uncertainties: list[str] = Field(default_factory=list)
    alternatives_considered: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    economic_summary: EconomicScenario | None = None


class DiligenceRequest(BaseModel):
    priority: str = Field(pattern="^P[0-2]$")
    request: str
    reason: str
    evidence_ids: list[UUID] = Field(default_factory=list)


class NegotiationRecommendation(BaseModel):
    action: str
    rationale: str
    evidence_ids: list[UUID] = Field(default_factory=list)


class InvestigationEvent(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    type: str
    message: str
    created_at: datetime = Field(default_factory=utcnow)
    data: dict[str, Any] = Field(default_factory=dict)


class InvestigationState(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    status: InvestigationStatus = InvestigationStatus.QUEUED
    input_type: InputType
    raw_input: str
    buyer_profile_id: UUID | None = None
    buyer_snapshot: BuyerProfileBase | None = None
    property: Property | None = None
    listing: ListingArtifact | None = None
    buyer_objectives: list[str] = Field(default_factory=list)
    user_objective: BuyerObjective = Field(default_factory=BuyerObjective)
    hypotheses: list[Hypothesis] = Field(default_factory=list)
    candidate_actions: list[InvestigationAction] = Field(default_factory=list)
    executed_actions: list[ExecutedAction] = Field(default_factory=list)
    budget_state: InvestigationBudget = Field(default_factory=InvestigationBudget)
    iteration: int = 0
    termination_reason: str | None = None
    claims: list[Claim] = Field(default_factory=list)
    claim_transitions: list[ClaimStateTransition] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    signals: list[DerivedSignal] = Field(default_factory=list)
    contradictions: list[Contradiction] = Field(default_factory=list)
    unknowns: list[Unknown] = Field(default_factory=list)
    relationships: list[EvidenceRelationship] = Field(default_factory=list)
    agent_runs: list[AgentRunArtifact] = Field(default_factory=list)
    agent_assessments: list[AgentAssessment] = Field(default_factory=list)
    tool_calls: list[ToolCallArtifact] = Field(default_factory=list)
    valuation: Valuation | None = None
    comparables: list[Comparable] = Field(default_factory=list)
    decision_stability: DecisionStability | None = None
    decision: Decision | None = None
    diligence: list[DiligenceRequest] = Field(default_factory=list)
    negotiation: list[NegotiationRecommendation] = Field(default_factory=list)
    crop_opportunities: list[CropOpportunity] = Field(default_factory=list)
    activity_opportunities: list[AgriculturalActivityOpportunity] = Field(default_factory=list)
    economic_scenarios: list[EconomicScenario] = Field(default_factory=list)
    hazard_assessments: list[HazardAssessment] = Field(default_factory=list)
    alternatives: list[PropertyAlternative] = Field(default_factory=list)
    boundary: BoundaryRecord | None = None
    financial_inputs: FinancialInputs = Field(default_factory=FinancialInputs)
    investment_decision: InvestmentDecision | None = None
    searched_radii_miles: list[float] = Field(default_factory=list)
    events: list[InvestigationEvent] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class CreateInvestigationRequest(BaseModel):
    input_type: InputType
    input: str = Field(min_length=3)
    buyer_profile_id: UUID | None = None
    objective: BuyerObjective | None = None

    @model_validator(mode="before")
    @classmethod
    def normalize_v2_input(cls, value):
        if isinstance(value, dict) and isinstance(value.get("input"), dict):
            payload = dict(value)
            nested = payload["input"]
            nested_type = nested.get("type", payload.get("input_type", "query"))
            aliases = {"listing": "listing_url", "coordinate": "location", "requirement": "query"}
            payload["input_type"] = aliases.get(nested_type, nested_type)
            raw_value = nested.get("value") or nested.get("url") or nested.get("text")
            if (
                raw_value is None
                and nested.get("latitude") is not None
                and nested.get("longitude") is not None
            ):
                raw_value = f"{nested['latitude']},{nested['longitude']}"
            payload["input"] = raw_value
            return payload
        return value

    @model_validator(mode="after")
    def validate_input_shape(self):
        if self.input_type == InputType.LISTING_URL:
            HttpUrl(self.input)
        return self


class InvestigationQuestionRequest(BaseModel):
    answer: str = Field(min_length=1)


class BoundaryUpdateRequest(BaseModel):
    geometry: dict[str, Any]
    kind: BoundaryKind = BoundaryKind.USER_UPLOADED
    source_name: str = "User-provided boundary"
    source_url: str | None = None


class FinancialInputsUpdate(BaseModel):
    financial_inputs: FinancialInputs


class EconomicAssumptionUpdate(BaseModel):
    activity: str = Field(min_length=2)
    production_per_unit: float = Field(gt=0)
    price_per_unit: float = Field(gt=0)
    operating_cost_per_unit: float = Field(gt=0)
    productive_units: float | None = Field(default=None, gt=0)
    production_unit: str = Field(default="units/acre", min_length=1)
    price_unit: str = Field(default="USD/unit", min_length=1)
    cost_unit: str = Field(default="USD/acre", min_length=1)
    source_name: str = Field(min_length=3)
    source_url: str | None = None
    vintage: str | None = None
    geography: str | None = None
    confidence: float = Field(default=0.6, ge=0, le=1)


class AgricultureEvaluationRequest(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    acreage: float | None = Field(default=None, gt=0)
    purchase_price: float | None = Field(default=None, gt=0)
    objective: BuyerObjective = Field(default_factory=BuyerObjective)
    evidence: list[Evidence] = Field(default_factory=list)


class OpportunitySearchRequest(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    objective: BuyerObjective = Field(default_factory=BuyerObjective)
    radius_miles: float = Field(default=10, gt=0, le=250)


class CreateInvestigationResponse(BaseModel):
    investigation_id: UUID
    status: InvestigationStatus


class ClaimTransitionProposal(BaseModel):
    claim_id: UUID
    target_state: ClaimState
    evidence_ids: list[UUID]
    confidence: float = Field(ge=0, le=1)
    rationale: str


class ToolResult(BaseModel):
    tool_name: str
    success: bool
    observations: list[Evidence] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    cost: float = 0
    raw_metadata: dict[str, Any] = Field(default_factory=dict)
