from fastapi import APIRouter

from app.connectors.listing_providers import configured_listing_provider
from app.domain.models import OpportunitySearchRequest
from app.opportunities.engine import OpportunityDiscoveryEngine

router = APIRouter()


@router.post("/search")
async def search_opportunities(payload: OpportunitySearchRequest):
    alternatives, radii = await OpportunityDiscoveryEngine(configured_listing_provider()).search(
        payload.latitude,
        payload.longitude,
        payload.objective,
        payload.radius_miles,
    )
    return {
        "status": "completed" if alternatives else "unavailable",
        "search_region": {
            "origin": [payload.longitude, payload.latitude],
            "radii_miles": radii,
        },
        "alternatives": alternatives,
        "limitations": []
        if alternatives
        else [
            "No permitted listing search provider is configured or no matching listings were returned.",
            "Configure LISTING_SEARCH_URL or seed reviewed listings before adaptive discovery.",
        ],
    }
