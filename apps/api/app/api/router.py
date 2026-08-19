from fastapi import APIRouter

from app.api.routes import evidence, investigations, profiles

api_router = APIRouter()
api_router.include_router(investigations.router, prefix="/investigations", tags=["investigations"])
api_router.include_router(evidence.router, prefix="/investigations", tags=["evidence"])
api_router.include_router(profiles.router, prefix="/buyer-profiles", tags=["buyer profiles"])
