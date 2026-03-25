from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.traveller_memory import TravellerMemoryRecord
from app.schemas.traveller_memory import (
    TravellerMemoryCreateRequest,
    TravellerMemoryCreateResponse,
    TravellerMemoryItem,
    TravellerMemoryListResponse,
)


def create_traveller_memory(
    db: Session,
    payload: TravellerMemoryCreateRequest,
) -> TravellerMemoryCreateResponse:
    record = TravellerMemoryRecord(
        traveller_id=payload.traveller_id,
        event_type=payload.event_type,
        source_surface=payload.source_surface,
        payload=payload.payload,
    )

    db.add(record)
    db.commit()
    db.refresh(record)

    return TravellerMemoryCreateResponse(
        id=record.id,
        traveller_id=record.traveller_id,
        event_type=record.event_type,
        source_surface=record.source_surface,
        payload=record.payload,
        created_at=record.created_at,
        saved=True,
    )


def get_recent_traveller_memory_records(
    db: Session,
    traveller_id: str,
    limit: int = 20,
    event_type: str | None = None,
    planning_session_id: str | None = None,
) -> list[TravellerMemoryRecord]:
    query = (
        db.query(TravellerMemoryRecord)
        .filter(TravellerMemoryRecord.traveller_id == traveller_id)
        .order_by(desc(TravellerMemoryRecord.created_at), desc(TravellerMemoryRecord.id))
    )

    if event_type:
        query = query.filter(TravellerMemoryRecord.event_type == event_type)

    records = query.limit(200).all()

    if planning_session_id:
        records = [
            record
            for record in records
            if str(record.payload.get("planning_session_id") or "") == planning_session_id
        ]

    return records[:limit]


def list_traveller_memory(
    db: Session,
    traveller_id: str,
    limit: int = 20,
    event_type: str | None = None,
    planning_session_id: str | None = None,
) -> TravellerMemoryListResponse:
    records = get_recent_traveller_memory_records(
        db=db,
        traveller_id=traveller_id,
        limit=limit,
        event_type=event_type,
        planning_session_id=planning_session_id,
    )

    items = [
        TravellerMemoryItem(
            id=record.id,
            traveller_id=record.traveller_id,
            event_type=record.event_type,
            source_surface=record.source_surface,
            payload=record.payload,
            created_at=record.created_at,
        )
        for record in records
    ]

    return TravellerMemoryListResponse(
        traveller_id=traveller_id,
        total=len(items),
        items=items,
    )