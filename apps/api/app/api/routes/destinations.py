from fastapi import APIRouter

from app.schemas.destination import (
    DestinationGuideRequest,
    DestinationGuideResponse,
    DestinationSearchRequest,
    DestinationSearchResponse,
)
from app.services.destination_service import build_destination_guide, search_destinations

router = APIRouter(prefix="/destinations", tags=["destinations"])


@router.post("/search", response_model=DestinationSearchResponse)
def search_destination_locations(
    payload: DestinationSearchRequest,
) -> DestinationSearchResponse:
    return search_destinations(payload)


@router.post("/guide", response_model=DestinationGuideResponse)
def generate_destination_guide(
    payload: DestinationGuideRequest,
) -> DestinationGuideResponse:
    return build_destination_guide(payload)