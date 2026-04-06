from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.embedding import EmbeddingResponse
from app.services.persona_embedding_service import generate_and_persist_persona_embedding

router = APIRouter(prefix="/persona-embeddings", tags=["persona-embeddings"])


class PersonaEmbeddingRequest(BaseModel):
    traveller_id: str = Field(..., min_length=1)
    provider: str | None = None


@router.post("/generate-and-save", response_model=EmbeddingResponse)
def generate_and_save_persona_embedding(
    payload: PersonaEmbeddingRequest,
    db: Session = Depends(get_db),
) -> EmbeddingResponse:
    try:
        return generate_and_persist_persona_embedding(
            db=db,
            traveller_id=payload.traveller_id,
            provider_override=payload.provider,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
