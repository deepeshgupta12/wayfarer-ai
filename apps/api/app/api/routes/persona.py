from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.persona import TravellerPersonaRecord
from app.schemas.persona import (
    TravellerPersonaInitializeRequest,
    TravellerPersonaInput,
    TravellerPersonaOutput,
    TravellerPersonaPersistedOutput,
)
from app.services.persona_service import (
    build_initial_persona,
    initialize_and_persist_persona,
    refresh_persona_from_memory,
)

router = APIRouter(prefix="/persona", tags=["persona"])


@router.get("/{traveller_id}", response_model=TravellerPersonaPersistedOutput)
def get_traveller_persona(
    traveller_id: str,
    db: Session = Depends(get_db),
) -> TravellerPersonaPersistedOutput:
    """Retrieve the persisted persona for a given traveller_id."""
    record: TravellerPersonaRecord | None = (
        db.query(TravellerPersonaRecord)
        .filter(TravellerPersonaRecord.traveller_id == traveller_id)
        .first()
    )
    if record is None:
        raise HTTPException(status_code=404, detail=f"No persona found for traveller_id={traveller_id}")
    return TravellerPersonaPersistedOutput(
        traveller_id=record.traveller_id,
        archetype=record.archetype,
        summary=record.summary,
        signals={
            "travel_style": record.travel_style,
            "pace_preference": record.pace_preference,
            "group_type": record.group_type,
            "interests": record.interests,
        },
    )


@router.post("/initialize", response_model=TravellerPersonaOutput)
def initialize_persona(payload: TravellerPersonaInput) -> TravellerPersonaOutput:
    return build_initial_persona(payload)


@router.post("/initialize-and-save", response_model=TravellerPersonaPersistedOutput)
def initialize_and_save_persona(
    payload: TravellerPersonaInitializeRequest,
    db: Session = Depends(get_db),
) -> TravellerPersonaPersistedOutput:
    return initialize_and_persist_persona(db, payload)


@router.delete("/{traveller_id}", status_code=204)
def delete_traveller_persona(
    traveller_id: str,
    db: Session = Depends(get_db),
) -> Response:
    """Hard-delete all persona data for a given traveller_id."""
    deleted = (
        db.query(TravellerPersonaRecord)
        .filter(TravellerPersonaRecord.traveller_id == traveller_id)
        .first()
    )
    if deleted is None:
        raise HTTPException(status_code=404, detail=f"No persona found for traveller_id={traveller_id}")
    db.delete(deleted)
    db.commit()
    return Response(status_code=204)


@router.post("/refresh-from-memory/{traveller_id}", response_model=TravellerPersonaPersistedOutput)
def refresh_persona_using_memory(
    traveller_id: str,
    db: Session = Depends(get_db),
) -> TravellerPersonaPersistedOutput:
    try:
        return refresh_persona_from_memory(db, traveller_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
