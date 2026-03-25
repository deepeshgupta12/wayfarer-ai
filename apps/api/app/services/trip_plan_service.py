import re
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.persona import TravellerPersonaRecord
from app.models.trip_plan import TripPlanRecord
from app.schemas.trip_plan import (
    ParsedTripConstraints,
    TripBriefParseRequest,
    TripPlanResponse,
    TripPlanSummaryResponse,
)

ALLOWED_INTERESTS = ["food", "culture", "adventure", "nature", "luxury", "nightlife", "wellness"]
DESTINATION_HINTS = [
    "tokyo",
    "kyoto",
    "lisbon",
    "prague",
    "budapest",
    "barcelona",
    "rome",
    "paris",
    "london",
    "bangkok",
    "bali",
    "singapore",
    "amsterdam",
    "seoul",
]

INTEREST_KEYWORDS: dict[str, list[str]] = {
    "food": ["food", "foodie", "cuisine", "eat", "restaurant", "dining", "brunch"],
    "culture": ["culture", "history", "heritage", "museum", "temple", "architecture"],
    "adventure": ["adventure", "hiking", "trek", "outdoors", "surf", "kayak"],
    "nature": ["nature", "park", "mountain", "beach", "river", "scenic", "gardens"],
    "luxury": ["luxury", "premium", "upscale", "boutique", "fine dining"],
    "nightlife": ["nightlife", "bar", "club", "music", "late night"],
    "wellness": ["wellness", "spa", "retreat", "relax", "onsen"],
}


def _get_persona_defaults(db: Session, traveller_id: str) -> dict[str, object]:
    persona = db.get(TravellerPersonaRecord, traveller_id)
    if persona is None:
        return {
            "group_type": None,
            "interests": [],
            "pace_preference": None,
            "budget": None,
        }

    return {
        "group_type": persona.group_type,
        "interests": list(persona.interests or []),
        "pace_preference": persona.pace_preference,
        "budget": persona.travel_style,
    }


def _extract_duration_days(brief: str) -> int | None:
    lowered = brief.lower()

    match = re.search(r"(\d+)\s*days?", lowered)
    if match:
        return int(match.group(1))

    match = re.search(r"(\d+)\s*nights?", lowered)
    if match:
        nights = int(match.group(1))
        return nights + 1

    weekend_terms = ["weekend", "2-day", "2 day"]
    if any(term in lowered for term in weekend_terms):
        return 2

    return None


def _extract_destination(brief: str) -> str | None:
    lowered = brief.lower()

    for destination in DESTINATION_HINTS:
        if destination in lowered:
            return destination.title()

    match = re.search(r"\bin\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)", brief)
    if match:
        return match.group(1).strip()

    return None


def _extract_group_type(brief: str) -> str | None:
    lowered = brief.lower()

    if "couple" in lowered or "partner" in lowered:
        return "couple"
    if "family" in lowered or "kids" in lowered or "kid-friendly" in lowered:
        return "family"
    if "friends" in lowered or "group trip" in lowered:
        return "friends"
    if "solo" in lowered or "just me" in lowered:
        return "solo"

    return None


def _extract_budget(brief: str) -> str | None:
    lowered = brief.lower()

    if "mid-budget" in lowered or "mid budget" in lowered or "midrange" in lowered:
        return "midrange"
    if "budget" in lowered and "mid-budget" not in lowered and "mid budget" not in lowered:
        return "budget"
    if "luxury" in lowered or "premium" in lowered or "upscale" in lowered:
        return "luxury"

    return None


def _extract_pace(brief: str) -> str | None:
    lowered = brief.lower()

    if any(term in lowered for term in ["relaxed", "calm", "slow", "easy-paced", "less hectic"]):
        return "relaxed"
    if any(term in lowered for term in ["fast", "packed", "hectic", "action-packed", "non-stop"]):
        return "fast"
    if "balanced" in lowered:
        return "balanced"

    return None


def _extract_interests(brief: str) -> list[str]:
    lowered = brief.lower()
    matches: list[str] = []

    for interest, keywords in INTEREST_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            matches.append(interest)

    return matches


def _merge_with_persona_defaults(
    parsed: dict[str, object],
    defaults: dict[str, object],
) -> ParsedTripConstraints:
    parsed_interests = list(parsed.get("interests") or [])
    default_interests = list(defaults.get("interests") or [])

    interests = parsed_interests or default_interests
    if len(interests) > 3:
        interests = interests[:3]

    return ParsedTripConstraints(
        destination=parsed.get("destination"),
        duration_days=parsed.get("duration_days"),
        group_type=parsed.get("group_type") or defaults.get("group_type"),
        interests=interests,
        pace_preference=parsed.get("pace_preference") or defaults.get("pace_preference"),
        budget=parsed.get("budget") or defaults.get("budget"),
    )


def _build_missing_fields(parsed_constraints: ParsedTripConstraints) -> list[str]:
    missing: list[str] = []

    if not parsed_constraints.destination:
        missing.append("destination")
    if not parsed_constraints.duration_days:
        missing.append("duration_days")
    if not parsed_constraints.group_type:
        missing.append("group_type")
    if not parsed_constraints.budget:
        missing.append("budget")
    if not parsed_constraints.pace_preference:
        missing.append("pace_preference")
    if not parsed_constraints.interests:
        missing.append("interests")

    return missing


def parse_and_save_trip_brief(
    db: Session,
    payload: TripBriefParseRequest,
) -> TripPlanResponse:
    defaults = _get_persona_defaults(db, payload.traveller_id)

    parsed = {
        "destination": _extract_destination(payload.brief),
        "duration_days": _extract_duration_days(payload.brief),
        "group_type": _extract_group_type(payload.brief),
        "interests": _extract_interests(payload.brief),
        "pace_preference": _extract_pace(payload.brief),
        "budget": _extract_budget(payload.brief),
    }

    parsed_constraints = _merge_with_persona_defaults(parsed, defaults)
    missing_fields = _build_missing_fields(parsed_constraints)
    planning_session_id = f"plan_{uuid4().hex}"

    record = TripPlanRecord(
        planning_session_id=planning_session_id,
        traveller_id=payload.traveller_id,
        source_surface=payload.source_surface,
        raw_brief=payload.brief,
        destination=parsed_constraints.destination,
        duration_days=parsed_constraints.duration_days,
        group_type=parsed_constraints.group_type,
        interests=list(parsed_constraints.interests),
        pace_preference=parsed_constraints.pace_preference,
        budget=parsed_constraints.budget,
        missing_fields=missing_fields,
        status="draft",
    )

    db.add(record)
    db.commit()
    db.refresh(record)

    return TripPlanResponse(
        planning_session_id=record.planning_session_id,
        traveller_id=record.traveller_id,
        source_surface=record.source_surface,
        raw_brief=record.raw_brief,
        parsed_constraints=parsed_constraints,
        missing_fields=list(record.missing_fields or []),
        status=record.status,
        saved=True,
        created_at=record.created_at,
    )


def get_trip_plan_summary(
    db: Session,
    planning_session_id: str,
) -> TripPlanSummaryResponse:
    record = (
        db.query(TripPlanRecord)
        .filter(TripPlanRecord.planning_session_id == planning_session_id)
        .first()
    )

    if record is None:
        raise ValueError(f"Trip plan not found for planning_session_id={planning_session_id}")

    parsed_constraints = ParsedTripConstraints(
        destination=record.destination,
        duration_days=record.duration_days,
        group_type=record.group_type,
        interests=list(record.interests or []),
        pace_preference=record.pace_preference,
        budget=record.budget,
    )

    return TripPlanSummaryResponse(
        planning_session_id=record.planning_session_id,
        traveller_id=record.traveller_id,
        source_surface=record.source_surface,
        raw_brief=record.raw_brief,
        parsed_constraints=parsed_constraints,
        missing_fields=list(record.missing_fields or []),
        status=record.status,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )