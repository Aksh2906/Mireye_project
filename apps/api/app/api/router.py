from fastapi import APIRouter

from app.api.routes import (
    agriculture,
    decision_intelligence,
    evidence,
    investigations,
    opportunities,
    profiles,
)

api_router = APIRouter()
api_router.include_router(investigations.router, prefix="/investigations", tags=["investigations"])
api_router.include_router(evidence.router, prefix="/investigations", tags=["evidence"])
api_router.include_router(profiles.router, prefix="/buyer-profiles", tags=["buyer profiles"])
api_router.include_router(agriculture.router, prefix="/agriculture", tags=["agriculture"])
api_router.include_router(opportunities.router, prefix="/opportunities", tags=["opportunities"])
api_router.include_router(
    decision_intelligence.router, prefix="/investigations", tags=["decision intelligence"]
)
