from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.domain.models import BuyerProfile, BuyerProfileBase, BuyerProfileUpdate, utcnow
from app.world_model.repository import repository

router = APIRouter()


@router.post("", response_model=BuyerProfile, status_code=201)
def create_profile(payload: BuyerProfileBase) -> BuyerProfile:
    return repository.save_profile(BuyerProfile(**payload.model_dump()))


@router.get("", response_model=list[BuyerProfile])
def list_profiles() -> list[BuyerProfile]:
    return repository.list_profiles()


@router.get("/{profile_id}", response_model=BuyerProfile)
def get_profile(profile_id: UUID) -> BuyerProfile:
    profile = repository.get_profile(profile_id)
    if not profile:
        raise HTTPException(404, "Buyer profile not found")
    return profile


@router.put("/{profile_id}", response_model=BuyerProfile)
def update_profile(profile_id: UUID, payload: BuyerProfileUpdate) -> BuyerProfile:
    current = repository.get_profile(profile_id)
    if not current:
        raise HTTPException(404, "Buyer profile not found")
    updated = BuyerProfile(
        id=current.id, created_at=current.created_at, updated_at=utcnow(), **payload.model_dump()
    )
    return repository.save_profile(updated)
