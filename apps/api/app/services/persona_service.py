from sqlalchemy.orm import Session

from app.models.persona import TravellerPersonaRecord
from app.schemas.persona import (
    TravellerPersonaInitializeRequest,
    TravellerPersonaInput,
    TravellerPersonaOutput,
    TravellerPersonaPersistedOutput,
)


def _detect_archetype(payload: TravellerPersonaInput) -> str:
    interests = set(payload.interests)

    if payload.travel_style == "luxury" or "luxury" in interests:
        return "luxury seeker"

    if payload.group_type == "family":
        return "family explorer"

    if "food" in interests and "culture" in interests:
        return "food and culture explorer"

    if "adventure" in interests and payload.pace_preference == "fast":
        return "adventure traveller"

    if payload.travel_style == "budget" and payload.group_type == "solo":
        return "budget backpacker"

    if "wellness" in interests and payload.pace_preference == "relaxed":
        return "slow wellness traveller"

    return "comfort-seeking explorer"


def _build_summary(archetype: str, payload: TravellerPersonaInput) -> str:
    interests_text = ", ".join(payload.interests)
    return (
        f"You travel like a {archetype} with a {payload.pace_preference} pace, "
        f"usually in a {payload.group_type} setting, with strong interest in {interests_text}."
    )


def build_initial_persona(payload: TravellerPersonaInput) -> TravellerPersonaOutput:
    archetype = _detect_archetype(payload)

    return TravellerPersonaOutput(
        archetype=archetype,
        summary=_build_summary(archetype, payload),
        signals={
            "travel_style": payload.travel_style,
            "pace_preference": payload.pace_preference,
            "group_type": payload.group_type,
            "interests": payload.interests,
        },
    )


def initialize_and_persist_persona(
    db: Session,
    payload: TravellerPersonaInitializeRequest,
) -> TravellerPersonaPersistedOutput:
    persona = build_initial_persona(payload)

    record = TravellerPersonaRecord(
        traveller_id=payload.traveller_id,
        archetype=persona.archetype,
        summary=persona.summary,
        travel_style=payload.travel_style,
        pace_preference=payload.pace_preference,
        group_type=payload.group_type,
        interests=list(payload.interests),
    )

    db.merge(record)
    db.commit()

    return TravellerPersonaPersistedOutput(
        traveller_id=payload.traveller_id,
        archetype=persona.archetype,
        summary=persona.summary,
        signals=persona.signals,
    )