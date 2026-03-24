from sqlalchemy.orm import Session

from app.models.persona import TravellerPersonaRecord
from app.schemas.persona import (
    TravellerPersonaInitializeRequest,
    TravellerPersonaInput,
    TravellerPersonaOutput,
    TravellerPersonaPersistedOutput,
)
from app.services.traveller_memory_service import get_recent_traveller_memory_records

ALLOWED_INTERESTS = ["food", "culture", "adventure", "nature", "luxury", "nightlife", "wellness"]
ALLOWED_PACES = ["relaxed", "balanced", "fast"]
ALLOWED_GROUPS = ["solo", "couple", "family", "friends"]
ALLOWED_STYLES = ["budget", "midrange", "luxury"]

QUERY_INTEREST_HINTS: dict[str, list[str]] = {
    "food": ["food", "foodie", "cuisine", "restaurant", "eat", "dining"],
    "culture": ["culture", "history", "heritage", "museum", "temple", "old town"],
    "adventure": ["adventure", "hiking", "trek", "outdoors", "kayak", "surf"],
    "nature": ["nature", "scenic", "park", "mountain", "beach", "river"],
    "luxury": ["luxury", "premium", "boutique", "fine dining", "upscale"],
    "nightlife": ["nightlife", "bar", "late night", "club", "music"],
    "wellness": ["wellness", "spa", "retreat", "relax", "onsen"],
}


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


def _infer_interests_from_query(query: str) -> list[str]:
    lowered = query.lower()
    inferred: list[str] = []

    for interest, keywords in QUERY_INTEREST_HINTS.items():
        if any(keyword in lowered for keyword in keywords):
            inferred.append(interest)

    return inferred


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


def refresh_persona_from_memory(
    db: Session,
    traveller_id: str,
) -> TravellerPersonaPersistedOutput:
    record = db.get(TravellerPersonaRecord, traveller_id)
    if record is None:
        raise ValueError(f"Traveller persona not found for traveller_id={traveller_id}")

    memory_records = get_recent_traveller_memory_records(
        db=db,
        traveller_id=traveller_id,
        limit=25,
    )

    interest_scores = {interest: 0.0 for interest in ALLOWED_INTERESTS}
    pace_scores = {pace: 0.0 for pace in ALLOWED_PACES}
    group_scores = {group: 0.0 for group in ALLOWED_GROUPS}
    style_scores = {style: 0.0 for style in ALLOWED_STYLES}

    for interest in record.interests:
        if interest in interest_scores:
            interest_scores[interest] += 2.0

    pace_scores[record.pace_preference] += 2.0
    group_scores[record.group_type] += 2.0
    style_scores[record.travel_style] += 2.0

    events_used = 0

    for memory_record in memory_records:
        payload = memory_record.payload if isinstance(memory_record.payload, dict) else {}
        event_weight = 1.5 if memory_record.event_type == "destination_guide_generated" else 1.0

        payload_interests = payload.get("interests", [])
        if isinstance(payload_interests, list):
            for interest in payload_interests:
                if interest in interest_scores:
                    interest_scores[interest] += 2.0 * event_weight

        query = payload.get("query")
        if isinstance(query, str) and query.strip():
            for interest in _infer_interests_from_query(query):
                interest_scores[interest] += 1.0 * event_weight

        traveller_type = payload.get("traveller_type")
        if traveller_type in group_scores:
            group_scores[traveller_type] += 2.5 * event_weight

        duration_days = payload.get("duration_days")
        if isinstance(duration_days, int):
            if duration_days <= 2:
                pace_scores["fast"] += 1.5 * event_weight
            elif duration_days >= 6:
                pace_scores["relaxed"] += 1.5 * event_weight
            else:
                pace_scores["balanced"] += 1.5 * event_weight

        budget = payload.get("budget")
        if budget in style_scores:
            style_scores[budget] += 2.0 * event_weight

        events_used += 1

    ranked_interests = [
        interest
        for interest, score in sorted(
            interest_scores.items(),
            key=lambda item: (item[1], item[0]),
            reverse=True,
        )
        if score > 0
    ]
    updated_interests = ranked_interests[:3] or list(record.interests)

    updated_pace = max(pace_scores.items(), key=lambda item: item[1])[0]
    updated_group = max(group_scores.items(), key=lambda item: item[1])[0]
    updated_style = max(style_scores.items(), key=lambda item: item[1])[0]

    refined_payload = TravellerPersonaInput(
        travel_style=updated_style,
        pace_preference=updated_pace,
        group_type=updated_group,
        interests=updated_interests,
    )

    refined_persona = build_initial_persona(refined_payload)

    record.archetype = refined_persona.archetype
    record.summary = refined_persona.summary
    record.travel_style = updated_style
    record.pace_preference = updated_pace
    record.group_type = updated_group
    record.interests = list(updated_interests)

    db.add(record)
    db.commit()

    return TravellerPersonaPersistedOutput(
        traveller_id=traveller_id,
        archetype=refined_persona.archetype,
        summary=refined_persona.summary,
        signals={
            "travel_style": updated_style,
            "pace_preference": updated_pace,
            "group_type": updated_group,
            "interests": updated_interests,
            "memory_events_used": events_used,
            "updated_from_memory": True,
        },
    )