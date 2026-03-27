from fastapi import APIRouter, Query

from app.db.session import get_db_session
from app.schemas.traveller_memory import (
    TravellerMemoryCreateRequest,
    TravellerMemoryCreateResponse,
    TravellerMemoryListResponse,
)
from app.services.traveller_memory_service import (
    create_traveller_memory,
    list_traveller_memory,
)

router = APIRouter(prefix="/traveller-memory", tags=["traveller-memory"])
legacy_router = APIRouter(tags=["traveller-memory"])


@router.post("", response_model=TravellerMemoryCreateResponse)
def create_memory_event(
    payload: TravellerMemoryCreateRequest,
) -> TravellerMemoryCreateResponse:
    db = get_db_session()
    try:
        return create_traveller_memory(db, payload)
    finally:
        db.close()


@router.get("/{traveller_id}", response_model=TravellerMemoryListResponse)
def get_memory_events(
    traveller_id: str,
    limit: int = Query(default=20, ge=1, le=100),
    event_type: str | None = Query(default=None),
    planning_session_id: str | None = Query(default=None),
) -> TravellerMemoryListResponse:
    db = get_db_session()
    try:
        return list_traveller_memory(
            db,
            traveller_id=traveller_id,
            limit=limit,
            event_type=event_type,
            planning_session_id=planning_session_id,
        )
    finally:
        db.close()

@legacy_router.get("/travellers/{traveller_id}/memory", response_model=TravellerMemoryListResponse)
def get_memory_events_legacy(
    traveller_id: str,
    limit: int = Query(default=20, ge=1, le=100),
    event_type: str | None = Query(default=None),
    planning_session_id: str | None = Query(default=None),
) -> TravellerMemoryListResponse:
    db = get_db_session()
    try:
        return list_traveller_memory(
            db,
            traveller_id=traveller_id,
            limit=limit,
            event_type=event_type,
            planning_session_id=planning_session_id,
        )
    finally:
        db.close()