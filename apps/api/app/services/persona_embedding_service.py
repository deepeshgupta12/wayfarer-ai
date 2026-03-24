from sqlalchemy.orm import Session

from app.models.persona import TravellerPersonaRecord
from app.models.persona_embedding import TravellerPersonaEmbeddingRecord
from app.schemas.embedding import EmbeddingResponse
from app.services.embedding_service import get_embedding


def build_persona_embedding_text(persona: TravellerPersonaRecord) -> str:
    interests_text = ", ".join(persona.interests)
    return (
        f"Traveller archetype: {persona.archetype}. "
        f"Travel style: {persona.travel_style}. "
        f"Pace: {persona.pace_preference}. "
        f"Group type: {persona.group_type}. "
        f"Interests: {interests_text}."
    )


def generate_and_persist_persona_embedding(
    db: Session,
    traveller_id: str,
    provider_override: str | None = None,
) -> EmbeddingResponse:
    persona = db.get(TravellerPersonaRecord, traveller_id)
    if persona is None:
        raise ValueError(f"No traveller persona found for traveller_id={traveller_id}")

    embedding_text = build_persona_embedding_text(persona)
    embedding = get_embedding(embedding_text, provider_override)

    record = TravellerPersonaEmbeddingRecord(
        traveller_id=traveller_id,
        provider=embedding.provider,
        model=embedding.model,
        dimensions=embedding.dimensions,
        vector=embedding.vector,
    )

    db.add(record)
    db.commit()

    return embedding