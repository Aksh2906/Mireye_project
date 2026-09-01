from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.agriculture.engine import (
    CROP_REGISTRY,
    AgricultureOpportunityEngine,
    HazardIntelligenceEngine,
)
from app.agriculture.finance import InvestmentEconomicsEngine
from app.connectors.agriculture import AgricultureAdapter
from app.connectors.economics import AgricultureEconomicsAdapter
from app.connectors.geospatial import BoundaryService, BoundaryValidationError, ParcelAdapter
from app.connectors.hazards import HazardAdapter
from app.connectors.listing_providers import configured_listing_provider
from app.connectors.mireye import MIREYE_HAZARD_FIELDS, MIREYE_LAND_USE_FIELDS
from app.domain.models import (
    BoundaryKind,
    BoundaryUpdateRequest,
    EconomicAssumptionUpdate,
    Evidence,
    EvidenceSource,
    FinancialInputsUpdate,
    InputType,
    InvestigationState,
    ListingArtifact,
    Property,
    SourceType,
)
from app.investigation.orchestrator import orchestrator
from app.opportunities.engine import OpportunityDiscoveryEngine
from app.world_model.repository import repository

router = APIRouter()
boundaries = BoundaryService()


async def _mireye_fields(latitude: float, longitude: float, fields: list[str]):
    """Use deterministic Mireye fetch, retaining compatibility with isolated test adapters."""
    fetch_fields = getattr(orchestrator.mireye, "fetch_fields", None)
    if fetch_fields:
        return await fetch_fields(latitude, longitude, fields)
    return await orchestrator.mireye.fetch_context(latitude, longitude, fields)


def _state(investigation_id: UUID) -> InvestigationState:
    state = repository.get(investigation_id)
    if not state:
        raise HTTPException(404, "Investigation not found")
    return state


def _boundary_evidence(state: InvestigationState) -> Evidence:
    assert state.boundary is not None
    boundary = state.boundary
    return Evidence(
        source_type=(
            SourceType.PARCEL
            if boundary.kind == BoundaryKind.AUTHORITATIVE_PARCEL
            else SourceType.USER_PROVIDED
        ),
        source=EvidenceSource(
            publisher=boundary.source_name,
            dataset="Property boundary geometry",
            url=boundary.source_url,
            retrieved_at=boundary.retrieved_at,
        ),
        field_name="property_boundary",
        value={
            "boundary_kind": boundary.kind,
            "area_acres": boundary.area_acres,
            "claimed_acres": boundary.claimed_acres,
            "acreage_difference": boundary.acreage_difference,
            "acreage_difference_percent": boundary.acreage_difference_percent,
            "is_legal_boundary": boundary.is_legal_boundary,
        },
        unit="acres",
        geometry=boundary.geometry.model_dump(mode="json"),
        semantic_scope="property boundary",
        confidence=boundary.confidence,
        limitations=boundary.limitations,
        raw_reference={"boundary_source": boundary.kind},
    )


@router.post("/{investigation_id}/boundary")
def set_boundary(investigation_id: UUID, payload: BoundaryUpdateRequest):
    state = _state(investigation_id)
    try:
        state.boundary = boundaries.build_record(
            payload.geometry,
            kind=payload.kind,
            source_name=payload.source_name,
            source_url=payload.source_url,
            claimed_acres=state.property.acreage if state.property else None,
            confidence=0.85 if payload.kind == BoundaryKind.USER_UPLOADED else 0.7,
        )
    except BoundaryValidationError as exc:
        raise HTTPException(422, str(exc)) from exc
    if state.property:
        state.property.geometry = state.boundary.geometry
    state.evidence = [item for item in state.evidence if item.field_name != "property_boundary"]
    state.evidence.append(_boundary_evidence(state))
    orchestrator.event(state, "boundary.updated", "Property boundary was validated and saved")
    orchestrator._analyze(state)
    repository.save(state)
    return {"status": "completed", "boundary": state.boundary}


@router.post("/{investigation_id}/actions/resolve-boundary")
async def resolve_boundary(investigation_id: UUID):
    state = _state(investigation_id)
    resolved = boundaries.resolve_from_state(state)
    if not resolved and state.property and state.property.latitude is not None:
        try:
            payload = await ParcelAdapter().lookup(
                state.property.latitude, state.property.longitude or 0
            )
            if payload:
                resolved = boundaries.build_record(
                    payload["geometry"],
                    kind=BoundaryKind.AUTHORITATIVE_PARCEL,
                    source_name=payload.get("source_name", "Configured parcel provider"),
                    source_url=payload.get("source_url"),
                    claimed_acres=state.property.acreage,
                    confidence=float(payload.get("confidence", 0.8)),
                    limitations=payload.get("limitations") or [],
                )
        except Exception as exc:
            state.limitations.append(f"Parcel boundary provider unavailable: {type(exc).__name__}")
    if (
        not resolved
        and state.property
        and state.property.latitude is not None
        and state.property.longitude is not None
        and state.property.acreage is not None
    ):
        resolved = boundaries.generate_analysis_geometry(
            state.property.latitude,
            state.property.longitude,
            state.property.acreage,
        )
    if not resolved:
        repository.save(state)
        return {
            "status": "unavailable",
            "boundary": None,
            "limitations": [
                "No listing geometry, user polygon, or configured parcel geometry was available."
            ],
        }
    state.boundary = resolved
    if state.property:
        state.property.geometry = resolved.geometry
    if not any(item.field_name == "property_boundary" for item in state.evidence):
        state.evidence.append(_boundary_evidence(state))
    orchestrator.event(state, "boundary.resolved", "Best available property boundary resolved")
    orchestrator._analyze(state)
    repository.save(state)
    return {"status": "completed", "boundary": state.boundary}


@router.post("/{investigation_id}/financial-inputs")
def update_financial_inputs(investigation_id: UUID, payload: FinancialInputsUpdate):
    state = _state(investigation_id)
    state.financial_inputs = payload.financial_inputs
    orchestrator._analyze(state)
    orchestrator.event(
        state,
        "economics.updated",
        "Financing and investment assumptions updated; economics recalculated",
    )
    repository.save(state)
    return {
        "financial_inputs": state.financial_inputs,
        "economic_scenarios": state.economic_scenarios,
        "investment_decision": state.investment_decision,
    }


@router.post("/{investigation_id}/economic-assumptions")
def update_economic_assumptions(investigation_id: UUID, payload: EconomicAssumptionUpdate):
    state = _state(investigation_id)
    activity = payload.activity.casefold().strip().replace(" ", "_")
    quantity_based = payload.productive_units is not None
    records = [
        (
            "production_per_unit" if quantity_based else "yield_per_acre",
            payload.production_per_unit,
            payload.production_unit,
        ),
        ("price_per_unit", payload.price_per_unit, payload.price_unit),
        (
            "operating_cost_per_unit" if quantity_based else "operating_cost_per_acre",
            payload.operating_cost_per_unit,
            payload.cost_unit,
        ),
    ]
    if payload.productive_units is not None:
        records.append(("productive_units", payload.productive_units, "head/units"))
    replacement_fields = {item[0] for item in records}
    state.evidence = [
        item
        for item in state.evidence
        if not (
            item.source_type == SourceType.USER_PROVIDED
            and item.field_name in replacement_fields
            and item.raw_reference.get("activity") == activity
        )
    ]
    state.evidence.extend(
        Evidence(
            source_type=SourceType.USER_PROVIDED,
            source=EvidenceSource(
                publisher=payload.source_name,
                dataset="User-supplied enterprise assumptions",
                url=payload.source_url,
                vintage=payload.vintage,
            ),
            field_name=field_name,
            value=value,
            unit=unit,
            semantic_scope=payload.geography or "user-specified planning assumption",
            confidence=payload.confidence,
            limitations=[
                "User-supplied planning input; verify against current local budgets, bids, and operating practices."
            ],
            raw_reference={"activity": activity, "entered_by": "user"},
        )
        for field_name, value, unit in records
    )
    orchestrator._analyze(state)
    orchestrator.event(
        state,
        "economics.assumptions_updated",
        f"Sourced planning assumptions updated for {activity.replace('_', ' ')}",
    )
    repository.save(state)
    return {
        "crop_opportunities": state.crop_opportunities,
        "activity_opportunities": state.activity_opportunities,
        "economic_scenarios": state.economic_scenarios,
        "investment_decision": state.investment_decision,
    }


@router.post("/{investigation_id}/actions/evaluate-uses")
async def evaluate_uses(investigation_id: UUID):
    state = _state(investigation_id)
    mireye_result = None
    if (
        state.property
        and state.property.latitude is not None
        and state.property.longitude is not None
    ):
        mireye_result = await _mireye_fields(
            state.property.latitude,
            state.property.longitude,
            MIREYE_LAND_USE_FIELDS,
        )
        existing = {(item.field_name, item.source.dataset) for item in state.evidence}
        for item in mireye_result.observations:
            key = (item.field_name, item.source.dataset)
            if key not in existing:
                state.evidence.append(item)
                existing.add(key)
        state.limitations = list(dict.fromkeys([*state.limitations, *mireye_result.limitations]))
    if not any(
        item.field_name in {"yield_per_acre", "expected_yield", "production_per_unit"}
        for item in state.evidence
    ):
        result = await AgricultureEconomicsAdapter().get_assumptions(
            state=state.property.state if state.property else None,
            county=state.property.county if state.property else None,
            activities=[item.value for item in state.user_objective.agricultural_activities],
            crops=list(CROP_REGISTRY),
        )
        economic_existing: set[tuple[str, str, str]] = {
            (item.field_name, str(item.raw_reference.get("activity")), item.source.dataset)
            for item in state.evidence
        }
        state.evidence.extend(
            item
            for item in result.observations
            if (item.field_name, str(item.raw_reference.get("activity")), item.source.dataset)
            not in economic_existing
        )
        state.limitations.extend(result.limitations)
    orchestrator._analyze(state)
    orchestrator.event(
        state,
        "uses.evaluated",
        "Mireye land, infrastructure, solar, wind, and agricultural uses recalculated"
        if mireye_result and mireye_result.success
        else "Agricultural uses recalculated; Mireye site screening unavailable",
    )
    repository.save(state)
    return {
        "crop_opportunities": state.crop_opportunities,
        "activity_opportunities": state.activity_opportunities,
        "economic_scenarios": state.economic_scenarios,
        "investment_decision": state.investment_decision,
    }


@router.post("/{investigation_id}/actions/analyze-hazards")
async def analyze_hazards(investigation_id: UUID):
    state = _state(investigation_id)
    if not state.property or state.property.latitude is None or state.property.longitude is None:
        raise HTTPException(409, "Property coordinates are required")
    mireye_result = await _mireye_fields(
        state.property.latitude,
        state.property.longitude,
        MIREYE_HAZARD_FIELDS,
    )
    provider_result = await HazardAdapter().get_context(
        state.property.latitude,
        state.property.longitude,
        list(HazardIntelligenceEngine.KEYWORDS),
        state.boundary.geometry.model_dump(mode="json") if state.boundary else None,
    )
    if mireye_result.success:
        state.evidence = [
            item for item in state.evidence if item.field_name not in {"mireye_hazard_report"}
        ]
    existing = {(item.field_name, item.source.dataset) for item in state.evidence}
    for result in (mireye_result, provider_result):
        for item in result.observations:
            key = (item.field_name, item.source.dataset)
            if key not in existing:
                state.evidence.append(item)
                existing.add(key)
    limitations = list(dict.fromkeys([*mireye_result.limitations, *provider_result.limitations]))
    state.limitations = list(dict.fromkeys([*state.limitations, *limitations]))
    orchestrator._analyze(state)
    success = mireye_result.success or provider_result.success
    orchestrator.event(
        state,
        "hazards.analyzed",
        "Mireye-first activity-specific hazards recalculated"
        if success
        else "Mireye and supplemental hazard provider unavailable; uncertainty preserved",
    )
    repository.save(state)
    return {
        "status": "completed" if success else "unavailable",
        "sources": {
            "mireye": "completed" if mireye_result.success else "unavailable",
            "supplemental_hazard_provider": (
                "completed" if provider_result.success else "unavailable"
            ),
        },
        "hazard_assessments": state.hazard_assessments,
        "limitations": limitations,
    }


@router.post("/{investigation_id}/actions/model-investment")
def model_investment(investigation_id: UUID):
    state = _state(investigation_id)
    AgricultureOpportunityEngine().evaluate(state)
    HazardIntelligenceEngine().evaluate(state)
    InvestmentEconomicsEngine().enrich(state)
    orchestrator.event(state, "investment.modeled", "Multi-year investment scenarios recalculated")
    repository.save(state)
    return {
        "economic_scenarios": state.economic_scenarios,
        "investment_decision": state.investment_decision,
    }


async def _deep_analyze_alternative(state: InvestigationState, alternative) -> None:
    if not alternative.location.coordinates or alternative.price is None:
        return
    longitude, latitude = alternative.location.coordinates[:2]
    temp = InvestigationState(
        input_type=InputType.LOCATION,
        raw_input=f"{latitude},{longitude}",
        property=Property(
            latitude=latitude,
            longitude=longitude,
            acreage=alternative.acreage,
        ),
        listing=ListingArtifact(
            url=alternative.source_url,
            asking_price=alternative.price,
            source="Nearby listing provider",
        ),
        user_objective=state.user_objective.model_copy(deep=True),
        financial_inputs=state.financial_inputs.model_copy(deep=True),
        evidence=[
            item.model_copy(deep=True)
            for item in state.evidence
            if item.source_type in {SourceType.USDA_AG_STATISTICS, SourceType.MARKET_DATA}
            and item.field_name
            in {
                "yield_per_acre",
                "expected_yield",
                "commodity_price",
                "price_per_unit",
                "operating_cost_per_acre",
            }
        ],
    )
    agriculture = AgricultureAdapter()
    year = datetime.now(UTC).year
    results = [
        await agriculture.get_crop_history(latitude, longitude, list(range(year - 5, year))),
        await agriculture.get_soil_context(latitude, longitude),
        await AgricultureEconomicsAdapter().get_assumptions(
            state=None,
            county=None,
            activities=[item.value for item in state.user_objective.agricultural_activities],
            crops=list(CROP_REGISTRY),
        ),
        await _mireye_fields(latitude, longitude, [*MIREYE_LAND_USE_FIELDS, *MIREYE_HAZARD_FIELDS]),
        await HazardAdapter().get_context(
            latitude, longitude, list(HazardIntelligenceEngine.KEYWORDS)
        ),
    ]
    for result in results:
        temp.evidence.extend(result.observations)
        temp.limitations.extend(result.limitations)
    AgricultureOpportunityEngine().evaluate(temp)
    HazardIntelligenceEngine().evaluate(temp)
    InvestmentEconomicsEngine().enrich(temp)
    alternative.economic_scenarios = temp.economic_scenarios
    alternative.evidence_quality = min(
        0.9, sum(item.confidence for item in temp.evidence) / max(1, len(temp.evidence))
    )
    alternative.investigation_depth = "deep"
    alternative.recommendation = (
        temp.investment_decision.label if temp.investment_decision else "Investigate"
    )
    if temp.investment_decision:
        alternative.advantages.extend(temp.investment_decision.rationale[:2])
        alternative.unknowns = temp.investment_decision.material_unknowns


@router.post("/{investigation_id}/actions/search-nearby")
async def search_nearby(investigation_id: UUID):
    state = _state(investigation_id)
    if not state.property or state.property.latitude is None or state.property.longitude is None:
        raise HTTPException(409, "Property coordinates are required")
    engine = OpportunityDiscoveryEngine(configured_listing_provider())
    alternatives, radii = await engine.search(
        state.property.latitude,
        state.property.longitude,
        state.user_objective,
    )
    for alternative in alternatives[:3]:
        await _deep_analyze_alternative(state, alternative)
    state.alternatives = alternatives
    state.searched_radii_miles = radii
    orchestrator.event(
        state,
        "alternatives.searched",
        f"Nearby search evaluated {len(alternatives)} candidate(s) across {len(radii)} radius step(s)",
    )
    repository.save(state)
    return {
        "status": "completed" if alternatives else "unavailable",
        "search_radii_miles": radii,
        "alternatives": alternatives,
        "limitations": []
        if alternatives
        else ["No permitted listing provider is configured or no matching listings were returned."],
    }


@router.post("/{investigation_id}/alternatives/{alternative_id}/investigate")
async def investigate_alternative(investigation_id: UUID, alternative_id: UUID):
    state = _state(investigation_id)
    alternative = next((item for item in state.alternatives if item.id == alternative_id), None)
    if not alternative:
        raise HTTPException(404, "Alternative not found")
    await _deep_analyze_alternative(state, alternative)
    repository.save(state)
    return alternative
