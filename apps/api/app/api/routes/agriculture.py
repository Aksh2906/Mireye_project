from fastapi import APIRouter

from app.agriculture.engine import AgricultureOpportunityEngine, HazardIntelligenceEngine
from app.domain.models import (
    AgricultureEvaluationRequest,
    InputType,
    InvestigationState,
    ListingArtifact,
    Property,
)

router = APIRouter()


@router.post("/evaluate")
def evaluate_agriculture(payload: AgricultureEvaluationRequest):
    state = InvestigationState(
        input_type=InputType.LOCATION,
        raw_input=f"{payload.latitude},{payload.longitude}",
        property=Property(
            latitude=payload.latitude, longitude=payload.longitude, acreage=payload.acreage
        ),
        listing=ListingArtifact(asking_price=payload.purchase_price),
        user_objective=payload.objective,
        evidence=payload.evidence,
    )
    AgricultureOpportunityEngine().evaluate(state)
    HazardIntelligenceEngine().evaluate(state)
    return {
        "crop_opportunities": state.crop_opportunities,
        "activity_opportunities": state.activity_opportunities,
        "economic_scenarios": state.economic_scenarios,
        "hazard_assessments": state.hazard_assessments,
        "limitations": []
        if payload.evidence
        else ["No evidence was supplied; opportunities remain unknown rather than inferred."],
    }
