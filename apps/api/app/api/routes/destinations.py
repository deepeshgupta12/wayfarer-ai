from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.db.session import get_db_session
from app.schemas.destination import (
    DestinationGuideRequest,
    DestinationGuideResponse,
    DestinationPlaceIndexRequest,
    DestinationPlaceIndexResponse,
    DestinationSearchRequest,
    DestinationSearchResponse,
    SimilarPlaceRequest,
    SimilarPlaceResponse,
)
from app.services.destination_service import (
    build_destination_guide,
    get_similar_places,
    index_destination_places,
    search_destinations,
    stream_destination_guide,
)

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


@router.post("/guide/stream")
def generate_destination_guide_stream(
    payload: DestinationGuideRequest,
) -> StreamingResponse:
    return StreamingResponse(
        stream_destination_guide(payload),
        media_type="application/x-ndjson",
    )


@router.post("/places/index", response_model=DestinationPlaceIndexResponse)
def create_destination_place_index(
    payload: DestinationPlaceIndexRequest,
) -> DestinationPlaceIndexResponse:
    db = get_db_session()
    try:
        return index_destination_places(db, payload)
    finally:
        db.close()


@router.post("/places/similar", response_model=SimilarPlaceResponse)
def get_destination_place_similarity(
    payload: SimilarPlaceRequest,
) -> SimilarPlaceResponse:
    db = get_db_session()
    try:
        return get_similar_places(db, payload)
    finally:
        db.close()