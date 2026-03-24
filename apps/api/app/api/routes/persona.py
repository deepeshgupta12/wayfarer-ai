from fastapi import APIRouter

from app.schemas.persona import TravellerPersonaInput, TravellerPersonaOutput
from app.services.persona_service import build_initial_persona

router = APIRouter(prefix="/persona", tags=["persona"])


@router.post("/initialize", response_model=TravellerPersonaOutput)
def initialize_persona(payload: TravellerPersonaInput) -> TravellerPersonaOutput:
    return build_initial_persona(payload)