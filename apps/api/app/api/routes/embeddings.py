from fastapi import APIRouter

from app.schemas.embedding import EmbeddingRequest, EmbeddingResponse
from app.services.embedding_service import get_embedding, get_embedding_provider_status

router = APIRouter(prefix="/embeddings", tags=["embeddings"])


@router.get("/status")
def embedding_status() -> dict[str, object]:
    return get_embedding_provider_status()


@router.post("/generate", response_model=EmbeddingResponse)
def generate_embedding(payload: EmbeddingRequest) -> EmbeddingResponse:
    return get_embedding(payload.text, payload.provider)