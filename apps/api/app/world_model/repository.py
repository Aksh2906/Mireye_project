from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from app.db import BuyerProfileRow, InvestigationRow, SessionLocal, initialize_database
from app.domain.models import BuyerProfile, InvestigationState, utcnow


class WorldModelRepository:
    def __init__(self) -> None:
        initialize_database()

    def save_profile(self, profile: BuyerProfile) -> BuyerProfile:
        with SessionLocal.begin() as session:
            row = session.get(BuyerProfileRow, str(profile.id))
            payload = profile.model_dump(mode="json")
            if row:
                row.payload = payload
                row.updated_at = utcnow()
            else:
                session.add(BuyerProfileRow(id=str(profile.id), payload=payload))
        return profile

    def get_profile(self, profile_id: UUID) -> BuyerProfile | None:
        with SessionLocal() as session:
            row = session.get(BuyerProfileRow, str(profile_id))
            return BuyerProfile.model_validate(row.payload) if row else None

    def list_profiles(self) -> list[BuyerProfile]:
        with SessionLocal() as session:
            rows = session.scalars(
                select(BuyerProfileRow).order_by(BuyerProfileRow.created_at)
            ).all()
            return [BuyerProfile.model_validate(row.payload) for row in rows]

    def save(self, state: InvestigationState) -> InvestigationState:
        self._normalize_limitations(state)
        state.updated_at = utcnow()
        with SessionLocal.begin() as session:
            row = session.get(InvestigationRow, str(state.id))
            payload = state.model_dump(mode="json")
            if row:
                row.status = state.status.value
                row.payload = payload
                row.updated_at = utcnow()
            else:
                session.add(
                    InvestigationRow(
                        id=str(state.id),
                        status=state.status.value,
                        input_type=state.input_type.value,
                        raw_input=state.raw_input,
                        payload=payload,
                    )
                )
        return state

    def get(self, investigation_id: UUID) -> InvestigationState | None:
        with SessionLocal() as session:
            row = session.get(InvestigationRow, str(investigation_id))
            if not row:
                return None
            state = InvestigationState.model_validate(row.payload)
            self._normalize_limitations(state)
            return state

    def list(self) -> list[InvestigationState]:
        with SessionLocal() as session:
            rows = session.scalars(
                select(InvestigationRow).order_by(InvestigationRow.created_at.desc())
            ).all()
            states = [InvestigationState.model_validate(row.payload) for row in rows]
            for state in states:
                self._normalize_limitations(state)
            return states

    @staticmethod
    def _normalize_limitations(state: InvestigationState) -> None:
        obsolete_prefixes = (
            "AGRICULTURE_ECONOMICS_URL is not configured",
            "HAZARD_API_URL is not configured",
        )
        normalized: list[str] = []
        for limitation in state.limitations:
            if limitation.startswith(obsolete_prefixes):
                continue
            if state.boundary and limitation.startswith("Boundary validation unavailable:"):
                continue
            if limitation not in normalized:
                normalized.append(limitation)
        state.limitations = normalized


repository = WorldModelRepository()
