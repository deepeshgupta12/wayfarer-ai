from fastapi import APIRouter

from app.db.session import get_db_session
from app.schemas.persona import (
    TravellerPersonaInitializeRequest,
    TravellerPersonaInput,
    TravellerPersonaOutput,
    TravellerPersonaPersistedOutput,
)
from app.services.persona_service import build_initial_persona, initialize_and_persist_persona

router = APIRouter(prefix="/persona", tags=["persona"])


@router.post("/initialize", response_model=TravellerPersonaOutput)
def initialize_persona(payload: TravellerPersonaInput) -> TravellerPersonaOutput:
    return build_initial_persona(payload)


@router.post("/initialize-and-save", response_model=TravellerPersonaPersistedOutput)
def initialize_and_save_persona(
    payload: TravellerPersonaInitializeRequest,
) -> TravellerPersonaPersistedOutput:
    db = get_db_session()
    try:
        return initialize_and_persist_persona(db, payload)
    finally:
        db.close()