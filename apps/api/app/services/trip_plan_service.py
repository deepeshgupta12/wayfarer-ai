import re
from uuid import uuid4

from sqlalchemy.orm import Session

from app.clients.tripadvisor_client import TripadvisorClient
from app.models.persona import TravellerPersonaRecord
from app.models.trip_plan import TripPlanRecord
from app.schemas.trip_plan import (
    ParsedTripConstraints,
    TripBriefParseRequest,
    TripCandidatePlace,
    TripDaySkeleton,
    TripPlanEnrichResponse,
    TripPlanResponse,
    TripPlanSummaryResponse,
)
from app.services.review_intelligence_service import analyze_review_bundle

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

tripadvisor_client = TripadvisorClient()


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


def _build_parsed_constraints_from_record(record: TripPlanRecord) -> ParsedTripConstraints:
    return ParsedTripConstraints(
        destination=record.destination,
        duration_days=record.duration_days,
        group_type=record.group_type,
        interests=list(record.interests or []),
        pace_preference=record.pace_preference,
        budget=record.budget,
    )


def _score_candidate_place(
    rating: float,
    review_count: int,
    authenticity_label: str | None,
    review_themes: dict[str, str],
) -> float:
    base_score = rating * 18.0
    volume_bonus = min(review_count / 5000.0, 1.0) * 8.0
    authenticity_bonus = {
        "high": 6.0,
        "medium": 3.0,
        "low": 0.0,
        None: 0.0,
    }.get(authenticity_label, 0.0)

    positive_theme_bonus = sum(1.5 for value in review_themes.values() if value == "positive")
    caution_penalty = sum(1.0 for value in review_themes.values() if value == "caution")

    return round(min(99.0, base_score + volume_bonus + authenticity_bonus + positive_theme_bonus - caution_penalty), 1)


def _build_why_selected(
    interests: list[str],
    review_themes: dict[str, str],
    authenticity_label: str | None,
) -> str:
    positive_themes = [theme.replace("_", " ") for theme, value in review_themes.items() if value == "positive"]
    interest_text = ", ".join(interests[:2]) if interests else "general exploration"

    if positive_themes:
        return (
            f"Selected for a {interest_text}-leaning trip, with positive review signals around "
            f"{', '.join(positive_themes[:2])} and {authenticity_label or 'unknown'} review confidence."
        )

    return (
        f"Selected as a relevant option for a {interest_text}-leaning trip, with "
        f"{authenticity_label or 'unknown'} review confidence."
    )


def _build_candidate_places(parsed_constraints: ParsedTripConstraints) -> list[TripCandidatePlace]:
    destination = parsed_constraints.destination
    if not destination:
        return []

    results = tripadvisor_client.search_locations(
        query=destination,
        traveller_type=parsed_constraints.group_type,
        interests=list(parsed_constraints.interests or []),
    )

    candidates: list[TripCandidatePlace] = []

    for result in results[:5]:
        review_bundle = tripadvisor_client.get_destination_reviews(result.name)
        review_analysis = analyze_review_bundle(
            location_id=str(review_bundle["location_id"]),
            location_name=str(review_bundle["location_name"]),
            reviews=list(review_bundle["reviews"]),
        )

        score = _score_candidate_place(
            rating=result.rating,
            review_count=result.review_count,
            authenticity_label=review_analysis.authenticity_label,
            review_themes=review_analysis.themes,
        )

        candidates.append(
            TripCandidatePlace(
                location_id=result.location_id,
                name=result.name,
                city=result.city,
                country=result.country,
                category=result.category,
                rating=result.rating,
                review_count=result.review_count,
                review_authenticity=review_analysis.authenticity_label,
                review_summary=review_analysis.quick_verdict,
                score=score,
                why_selected=_build_why_selected(
                    interests=list(parsed_constraints.interests or []),
                    review_themes=review_analysis.themes,
                    authenticity_label=review_analysis.authenticity_label,
                ),
            )
        )

    candidates.sort(key=lambda item: item.score, reverse=True)
    return candidates


def _day_title(day_number: int, total_days: int, pace: str | None) -> str:
    if day_number == 1:
        return "Arrival and orientation"
    if day_number == total_days:
        return "Flexible finale and wrap-up"
    if pace == "relaxed":
        return f"Slow exploration — Day {day_number}"
    if pace == "fast":
        return f"High-coverage exploration — Day {day_number}"
    return f"Core exploration — Day {day_number}"


def _day_summary(
    day_number: int,
    total_days: int,
    destination: str,
    interests: list[str],
    pace: str | None,
    place_names: list[str],
) -> str:
    interests_text = ", ".join(interests[:2]) if interests else "city discovery"

    if day_number == 1:
        return (
            f"Start lightly in {destination} with an easy introduction to the city and "
            f"one or two places aligned with {interests_text}."
        )

    if day_number == total_days:
        return (
            f"Keep the final day in {destination} flexible, using it for favorites, slower exploration, "
            f"or anything missed earlier."
        )

    if pace == "relaxed":
        return (
            f"Use Day {day_number} for lower-pressure exploration around {interests_text}, keeping transfers "
            f"lighter and focusing on depth over coverage."
        )

    if pace == "fast":
        return (
            f"Use Day {day_number} for broader coverage across strong candidate places in {destination}, "
            f"while still leaning into {interests_text}."
        )

    highlighted = ", ".join(place_names[:2]) if place_names else destination
    return (
        f"Use Day {day_number} for balanced exploration in {destination}, centered on {highlighted} and "
        f"guided by {interests_text}."
    )


def _build_itinerary_skeleton(
    parsed_constraints: ParsedTripConstraints,
    candidate_places: list[TripCandidatePlace],
) -> list[TripDaySkeleton]:
    duration_days = parsed_constraints.duration_days or 0
    destination = parsed_constraints.destination or "the destination"
    interests = list(parsed_constraints.interests or [])
    pace = parsed_constraints.pace_preference

    skeleton: list[TripDaySkeleton] = []

    if duration_days <= 0:
        return skeleton

    for day_number in range(1, duration_days + 1):
        assigned = [
            candidate
            for index, candidate in enumerate(candidate_places)
            if index % duration_days == (day_number - 1) % duration_days
        ]

        if not assigned and candidate_places:
            assigned = [candidate_places[min(day_number - 1, len(candidate_places) - 1)]]

        place_names = [candidate.name for candidate in assigned]
        candidate_ids = [candidate.location_id for candidate in assigned]

        skeleton.append(
            TripDaySkeleton(
                day_number=day_number,
                title=_day_title(day_number, duration_days, pace),
                summary=_day_summary(
                    day_number=day_number,
                    total_days=duration_days,
                    destination=destination,
                    interests=interests,
                    pace=pace,
                    place_names=place_names,
                ),
                place_names=place_names,
                candidate_location_ids=candidate_ids,
            )
        )

    return skeleton


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
        candidate_places=[],
        itinerary_skeleton=[],
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
        candidate_places=[],
        itinerary_skeleton=[],
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

    parsed_constraints = _build_parsed_constraints_from_record(record)
    candidate_places = [TripCandidatePlace(**item) for item in list(record.candidate_places or [])]
    itinerary_skeleton = [TripDaySkeleton(**item) for item in list(record.itinerary_skeleton or [])]

    return TripPlanSummaryResponse(
        planning_session_id=record.planning_session_id,
        traveller_id=record.traveller_id,
        source_surface=record.source_surface,
        raw_brief=record.raw_brief,
        parsed_constraints=parsed_constraints,
        missing_fields=list(record.missing_fields or []),
        status=record.status,
        candidate_places=candidate_places,
        itinerary_skeleton=itinerary_skeleton,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def enrich_trip_plan(
    db: Session,
    planning_session_id: str,
) -> TripPlanEnrichResponse:
    record = (
        db.query(TripPlanRecord)
        .filter(TripPlanRecord.planning_session_id == planning_session_id)
        .first()
    )

    if record is None:
        raise ValueError(f"Trip plan not found for planning_session_id={planning_session_id}")

    parsed_constraints = _build_parsed_constraints_from_record(record)
    missing_fields = _build_missing_fields(parsed_constraints)

    if missing_fields:
        raise RuntimeError(
            "Trip plan is incomplete for enrichment. Missing fields: "
            + ", ".join(missing_fields)
        )

    candidate_places = _build_candidate_places(parsed_constraints)
    itinerary_skeleton = _build_itinerary_skeleton(parsed_constraints, candidate_places)

    record.candidate_places = [item.model_dump() for item in candidate_places]
    record.itinerary_skeleton = [item.model_dump() for item in itinerary_skeleton]
    record.missing_fields = []
    record.status = "enriched"

    db.add(record)
    db.commit()
    db.refresh(record)

    return TripPlanEnrichResponse(
        planning_session_id=record.planning_session_id,
        traveller_id=record.traveller_id,
        source_surface=record.source_surface,
        raw_brief=record.raw_brief,
        parsed_constraints=parsed_constraints,
        missing_fields=[],
        status=record.status,
        candidate_places=candidate_places,
        itinerary_skeleton=itinerary_skeleton,
        saved=True,
        updated_at=record.updated_at,
    )