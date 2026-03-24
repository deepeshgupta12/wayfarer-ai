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
    limit: int = 25,
) -> list[TravellerMemoryRecord]:
    return (
        db.query(TravellerMemoryRecord)
        .filter(TravellerMemoryRecord.traveller_id == traveller_id)
        .order_by(desc(TravellerMemoryRecord.created_at), desc(TravellerMemoryRecord.id))
        .limit(limit)
        .all()
    )


def list_traveller_memory(
    db: Session,
    traveller_id: str,
    limit: int = 20,
) -> TravellerMemoryListResponse:
    records = get_recent_traveller_memory_records(
        db=db,
        traveller_id=traveller_id,
        limit=limit,
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