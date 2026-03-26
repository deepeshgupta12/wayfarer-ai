from __future__ import annotations

import math

from sqlalchemy import desc
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


def _cosine_similarity(vector_a: list[float], vector_b: list[float]) -> float:
    if not vector_a or not vector_b or len(vector_a) != len(vector_b):
        return 0.0

    dot_product = sum(a * b for a, b in zip(vector_a, vector_b))
    magnitude_a = math.sqrt(sum(a * a for a in vector_a))
    magnitude_b = math.sqrt(sum(b * b for b in vector_b))

    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0

    return dot_product / (magnitude_a * magnitude_b)


def get_latest_persona_embedding_record(
    db: Session,
    traveller_id: str,
) -> TravellerPersonaEmbeddingRecord | None:
    return (
        db.query(TravellerPersonaEmbeddingRecord)
        .filter(TravellerPersonaEmbeddingRecord.traveller_id == traveller_id)
        .order_by(desc(TravellerPersonaEmbeddingRecord.id))
        .first()
    )


def calculate_persona_relevance_score(
    db: Session,
    traveller_id: str,
    text: str,
) -> float | None:
    record = get_latest_persona_embedding_record(db, traveller_id)
    if record is None:
        return None

    embedding = get_embedding(text, provider_override=record.provider)

    if embedding.dimensions != record.dimensions:
        return None

    return round(
        max(0.0, _cosine_similarity(record.vector, embedding.vector)),
        4,
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