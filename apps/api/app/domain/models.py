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
    WEB_SOURCE = "WEB_SOURCE"
    DERIVED = "DERIVED"


class Materiality(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class Verdict(StrEnum):
    ACQUIRE = "ACQUIRE"
    DO_NOT_ACQUIRE = "DO_NOT_ACQUIRE"


class Geometry(BaseModel):
    type: str = "Point"
    coordinates: list[float] = Field(default_factory=list)


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
    events: list[InvestigationEvent] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class CreateInvestigationRequest(BaseModel):
    input_type: InputType
    input: str = Field(min_length=3)
    buyer_profile_id: UUID | None = None

    @model_validator(mode="after")
    def validate_input_shape(self):
        if self.input_type == InputType.LISTING_URL:
            HttpUrl(self.input)
        return self


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
