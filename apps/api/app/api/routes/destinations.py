from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.destination import (
    DestinationComparisonRequest,
    DestinationComparisonResponse,
    DestinationGuideRequest,
    DestinationGuideResponse,
    DestinationPlaceIndexRequest,
    DestinationPlaceIndexResponse,
    DestinationSearchRequest,
    DestinationSearchResponse,
    HiddenGemDiscoveryRequest,
    HiddenGemDiscoveryResponse,
    NearbyDiscoveryRequest,
    NearbyDiscoveryResponse,
    SimilarPlaceRequest,
    SimilarPlaceResponse,
)
from app.services.destination_service import (
    build_destination_guide,
    compare_destinations,
    discover_hidden_gems,
    get_similar_places,
    index_destination_places,
    search_destinations,
    stream_destination_guide,
)
from app.services.nearby_discovery_service import discover_context_aware_nearby_places

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


@router.post("/gems", response_model=HiddenGemDiscoveryResponse)
def discover_destination_hidden_gems(
    payload: HiddenGemDiscoveryRequest,
    db: Session = Depends(get_db),
) -> HiddenGemDiscoveryResponse:
    return discover_hidden_gems(db, payload)


@router.post("/nearby", response_model=NearbyDiscoveryResponse)
def discover_nearby_places(
    payload: NearbyDiscoveryRequest,
    db: Session = Depends(get_db),
) -> NearbyDiscoveryResponse:
    return discover_context_aware_nearby_places(db, payload)


@router.post("/guide/stream")
def generate_destination_guide_stream(
    payload: DestinationGuideRequest,
) -> StreamingResponse:
    return StreamingResponse(
        stream_destination_guide(payload),
        media_type="application/x-ndjson",
    )


@router.post("/compare", response_model=DestinationComparisonResponse)
def compare_destination_pair(
    payload: DestinationComparisonRequest,
) -> DestinationComparisonResponse:
    return compare_destinations(payload)


@router.post("/places/index", response_model=DestinationPlaceIndexResponse)
def create_destination_place_index(
    payload: DestinationPlaceIndexRequest,
    db: Session = Depends(get_db),
) -> DestinationPlaceIndexResponse:
    return index_destination_places(db, payload)


@router.post("/places/similar", response_model=SimilarPlaceResponse)
def get_destination_place_similarity(
    payload: SimilarPlaceRequest,
    db: Session = Depends(get_db),
) -> SimilarPlaceResponse:
    return get_similar_places(db, payload)
