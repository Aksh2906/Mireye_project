import asyncio
import json
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.domain.models import (
    BuyerProfileBase,
    CreateInvestigationRequest,
    CreateInvestigationResponse,
    InvestigationState,
)
from app.investigation.orchestrator import orchestrator
from app.reporting import generate_dossier
from app.world_model.repository import repository

router = APIRouter()


@router.post("", response_model=CreateInvestigationResponse, status_code=202)
async def create_investigation(
    payload: CreateInvestigationRequest, background: BackgroundTasks
) -> CreateInvestigationResponse:
    profile = repository.get_profile(payload.buyer_profile_id) if payload.buyer_profile_id else None
    if payload.buyer_profile_id and not profile:
        raise HTTPException(404, "Buyer profile not found")
    state = InvestigationState(
        input_type=payload.input_type,
        raw_input=payload.input,
        buyer_profile_id=payload.buyer_profile_id,
        buyer_snapshot=BuyerProfileBase.model_validate(
            profile.model_dump(exclude={"id", "created_at", "updated_at"})
        )
        if profile
        else None,
    )
    repository.save(state)
    background.add_task(orchestrator.run, state.id)
    return CreateInvestigationResponse(investigation_id=state.id, status=state.status)


@router.get("", response_model=list[InvestigationState])
def list_investigations() -> list[InvestigationState]:
    return repository.list()


@router.get("/{investigation_id}", response_model=InvestigationState)
def get_investigation(investigation_id: UUID) -> InvestigationState:
    state = repository.get(investigation_id)
    if not state:
        raise HTTPException(404, "Investigation not found")
    return state


@router.get("/{investigation_id}/events")
async def stream_events(
    investigation_id: UUID, cursor: int = Query(default=0, ge=0)
) -> StreamingResponse:
    if not repository.get(investigation_id):
        raise HTTPException(404, "Investigation not found")

    async def generate():
        index = cursor
        idle = 0
        while idle < 120:
            state = repository.get(investigation_id)
            if not state:
                return
            while index < len(state.events):
                event = state.events[index]
                yield f"id: {index}\nevent: {event.type}\ndata: {json.dumps(event.model_dump(mode='json'))}\n\n"
                index += 1
                idle = 0
            if state.status in {"completed", "failed", "needs_input"}:
                return
            idle += 1
            await asyncio.sleep(1)

    return StreamingResponse(
        generate(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"}
    )


@router.get("/{investigation_id}/valuation")
def get_valuation(investigation_id: UUID):
    state = get_investigation(investigation_id)
    return {
        "valuation": state.valuation,
        "comparables": state.comparables,
        "decision_stability": state.decision_stability,
    }


@router.get("/{investigation_id}/strategy")
def get_strategy(investigation_id: UUID):
    state = get_investigation(investigation_id)
    return {"diligence": state.diligence, "negotiation": state.negotiation}


@router.get("/{investigation_id}/dossier")
def get_dossier(investigation_id: UUID):
    return generate_dossier(get_investigation(investigation_id))
