from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.world_model.repository import repository

router = APIRouter()


def state_or_404(investigation_id: UUID):
    state = repository.get(investigation_id)
    if not state:
        raise HTTPException(404, "Investigation not found")
    return state


@router.get("/{investigation_id}/claims")
def claims(investigation_id: UUID):
    state = state_or_404(investigation_id)
    return {"claims": state.claims, "transitions": state.claim_transitions}


@router.get("/{investigation_id}/evidence")
def evidence(investigation_id: UUID):
    return state_or_404(investigation_id).evidence


@router.get("/{investigation_id}/signals")
def signals(investigation_id: UUID):
    return state_or_404(investigation_id).signals


@router.get("/{investigation_id}/contradictions")
def contradictions(investigation_id: UUID):
    return state_or_404(investigation_id).contradictions


@router.get("/{investigation_id}/unknowns")
def unknowns(investigation_id: UUID):
    return state_or_404(investigation_id).unknowns


@router.get("/{investigation_id}/trace")
def trace(investigation_id: UUID):
    state = state_or_404(investigation_id)
    return {
        "events": state.events,
        "agent_runs": state.agent_runs,
        "agent_assessments": state.agent_assessments,
        "tool_calls": state.tool_calls,
    }


@router.get("/{investigation_id}/graph")
def graph(investigation_id: UUID):
    state = state_or_404(investigation_id)
    nodes = (
        [{"id": str(x.id), "type": "CLAIM", "data": x} for x in state.claims]
        + [{"id": str(x.id), "type": "EVIDENCE", "data": x} for x in state.evidence]
        + [{"id": str(x.id), "type": "SIGNAL", "data": x} for x in state.signals]
        + [{"id": str(x.id), "type": "CONTRADICTION", "data": x} for x in state.contradictions]
    )
    return {"nodes": nodes, "edges": state.relationships}
