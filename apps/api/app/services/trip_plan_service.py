import re
from uuid import uuid4

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.clients.tripadvisor_client import TripadvisorClient
from app.models.persona import TravellerPersonaRecord
from app.models.saved_trip import ItineraryVersionRecord, SavedTripRecord, TripSignalRecord
from app.models.traveller_memory import TravellerMemoryRecord
from app.models.trip_plan import TripPlanRecord
from app.schemas.trip_plan import (
    ParsedTripConstraints,
    SavedTripListResponse,
    SavedTripSummaryResponse,
    TripAlternativeSuggestion,
    TripBriefParseRequest,
    TripCandidatePlace,
    TripDayPlan,
    TripPlanEnrichResponse,
    TripPlanResponse,
    TripPlanSummaryResponse,
    TripPlanUpdateRequest,
    TripPromoteRequest,
    TripSignalCreateRequest,
    TripSignalListResponse,
    TripSignalResponse,
    TripSlotAssignment,
    TripSlotReplacementRequest,
    TripVersionListResponse,
    TripVersionResponse,
    TripVersionSnapshotRequest,
)
from app.services.persona_embedding_service import calculate_persona_relevance_score
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
    "food": ["food", "foodie", "cuisine", "eat", "restaurant", "dining", "brunch", "market"],
    "culture": ["culture", "history", "heritage", "museum", "temple", "architecture", "shrine"],
    "adventure": ["adventure", "hiking", "trek", "outdoors", "surf", "kayak"],
    "nature": ["nature", "park", "mountain", "beach", "river", "scenic", "gardens", "bamboo"],
    "luxury": ["luxury", "premium", "upscale", "boutique", "fine dining"],
    "nightlife": ["nightlife", "bar", "club", "music", "late night"],
    "wellness": ["wellness", "spa", "retreat", "onsen"],
}

SLOT_SEQUENCE = [
    ("morning", "Morning"),
    ("lunch", "Lunch"),
    ("afternoon", "Afternoon"),
    ("evening", "Evening"),
]

CLUSTER_TRAVEL_COSTS: dict[tuple[str, str], float] = {
    ("central_core", "central_core"): 0.0,
    ("central_core", "heritage_core"): 1.5,
    ("central_core", "urban_core"): 1.5,
    ("central_core", "scenic_zone"): 3.0,
    ("heritage_core", "heritage_core"): 0.0,
    ("heritage_core", "urban_core"): 2.0,
    ("heritage_core", "scenic_zone"): 3.5,
    ("urban_core", "urban_core"): 0.0,
    ("urban_core", "scenic_zone"): 4.0,
    ("scenic_zone", "scenic_zone"): 0.0,
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


def _contains_interest_keyword(text: str, keyword: str) -> bool:
    if " " in keyword:
        return keyword in text
    return re.search(rf"\b{re.escape(keyword)}\b", text) is not None


def _extract_interests(brief: str) -> list[str]:
    lowered = brief.lower()
    matches: list[str] = []

    for interest, keywords in INTEREST_KEYWORDS.items():
        if any(_contains_interest_keyword(lowered, keyword) for keyword in keywords):
            matches.append(interest)

    return matches


def _normalize_interests(interests: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()

    for interest in interests:
        if interest not in ALLOWED_INTERESTS:
            continue
        if interest in seen:
            continue
        seen.add(interest)
        normalized.append(interest)

    return normalized[:3]


def _merge_with_persona_defaults(
    parsed: dict[str, object],
    defaults: dict[str, object],
) -> ParsedTripConstraints:
    parsed_interests = _normalize_interests(list(parsed.get("interests") or []))
    default_interests = _normalize_interests(list(defaults.get("interests") or []))

    interests = parsed_interests or default_interests

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
        interests=_normalize_interests(list(record.interests or [])),
        pace_preference=record.pace_preference,
        budget=record.budget,
    )


def _build_summary_response(record: TripPlanRecord) -> TripPlanSummaryResponse:
    parsed_constraints = _build_parsed_constraints_from_record(record)
    candidate_places = [TripCandidatePlace(**item) for item in list(record.candidate_places or [])]
    itinerary_skeleton = [TripDayPlan(**item) for item in list(record.itinerary_skeleton or [])]

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


def _score_candidate_place(
    rating: float,
    review_count: int,
    authenticity_label: str | None,
    review_themes: dict[str, str],
    persona_relevance_score: float | None = None,
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
    persona_bonus = (persona_relevance_score or 0.0) * 30.0

    return round(
        min(
            99.0,
            base_score + volume_bonus + authenticity_bonus + positive_theme_bonus - caution_penalty + persona_bonus,
        ),
        1,
    )


def _infer_geo_cluster(place_name: str, city: str, country: str) -> str:
    lowered = f"{place_name} {city} {country}".lower()

    if any(term in lowered for term in ["gion", "higashiyama", "temple", "heritage", "museum", "fushimi", "asakusa"]):
        return "heritage_core"
    if any(term in lowered for term in ["alfama", "chiado", "bairro", "nightlife", "bar", "shibuya", "pontocho", "kagurazaka"]):
        return "urban_core"
    if any(term in lowered for term in ["park", "garden", "scenic", "river", "arashiyama", "nature", "bamboo", "ueno"]):
        return "scenic_zone"

    return "central_core"


def _build_why_selected(
    interests: list[str],
    review_themes: dict[str, str],
    authenticity_label: str | None,
    persona_relevance_score: float | None = None,
) -> str:
    positive_themes = [theme.replace("_", " ") for theme, value in review_themes.items() if value == "positive"]
    interest_text = ", ".join(interests[:2]) if interests else "general exploration"

    persona_text = ""
    if persona_relevance_score is not None and persona_relevance_score >= 0.75:
        persona_text = " It also shows a strong persona-embedding fit for this traveller."

    if positive_themes:
        return (
            f"Selected for a {interest_text}-leaning trip, with positive review signals around "
            f"{', '.join(positive_themes[:2])} and {authenticity_label or 'unknown'} review confidence."
            f"{persona_text}"
        )

    return (
        f"Selected as a relevant option for a {interest_text}-leaning trip, with "
        f"{authenticity_label or 'unknown'} review confidence."
        f"{persona_text}"
    )

def _build_trip_candidate_embedding_text(
    destination: str,
    group_type: str | None,
    interests: list[str],
    place_name: str,
    city: str,
    country: str,
    category: str,
    rating: float,
    review_count: int,
    review_summary: str | None,
) -> str:
    interests_text = ", ".join(interests) if interests else "general exploration"
    group_text = group_type or "general traveller"
    summary_text = review_summary or "no review summary"

    return (
        f"destination={destination}; "
        f"name={place_name}; "
        f"city={city}; "
        f"country={country}; "
        f"category={category}; "
        f"group_type={group_text}; "
        f"interests={interests_text}; "
        f"rating={rating}; "
        f"review_count={review_count}; "
        f"review_summary={summary_text}"
    )


def _compute_trip_candidate_persona_relevance(
    db: Session,
    traveller_id: str,
    destination: str,
    group_type: str | None,
    interests: list[str],
    place_name: str,
    city: str,
    country: str,
    category: str,
    rating: float,
    review_count: int,
    review_summary: str | None,
) -> float | None:
    embedding_text = _build_trip_candidate_embedding_text(
        destination=destination,
        group_type=group_type,
        interests=interests,
        place_name=place_name,
        city=city,
        country=country,
        category=category,
        rating=rating,
        review_count=review_count,
        review_summary=review_summary,
    )

    return calculate_persona_relevance_score(
        db=db,
        traveller_id=traveller_id,
        text=embedding_text,
    )


def _build_candidate_places(
    db: Session,
    traveller_id: str,
    parsed_constraints: ParsedTripConstraints,
) -> list[TripCandidatePlace]:
    destination = parsed_constraints.destination
    if not destination:
        return []

    results = tripadvisor_client.search_locations(
        query=destination,
        traveller_type=parsed_constraints.group_type,
        interests=list(parsed_constraints.interests or []),
    )

    candidates: list[TripCandidatePlace] = []

    for result in results[:8]:
        review_bundle = tripadvisor_client.get_destination_reviews(result.name)
        review_analysis = analyze_review_bundle(
            location_id=str(review_bundle["location_id"]),
            location_name=str(review_bundle["location_name"]),
            reviews=list(review_bundle["reviews"]),
        )

        persona_relevance_score = _compute_trip_candidate_persona_relevance(
            db=db,
            traveller_id=traveller_id,
            destination=destination,
            group_type=parsed_constraints.group_type,
            interests=list(parsed_constraints.interests or []),
            place_name=result.name,
            city=result.city,
            country=result.country,
            category=result.category,
            rating=result.rating,
            review_count=result.review_count,
            review_summary=review_analysis.quick_verdict,
        )

        score = _score_candidate_place(
            rating=result.rating,
            review_count=result.review_count,
            authenticity_label=review_analysis.authenticity_label,
            review_themes=review_analysis.themes,
            persona_relevance_score=persona_relevance_score,
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
                    persona_relevance_score=persona_relevance_score,
                ),
                geo_cluster=_infer_geo_cluster(
                    place_name=result.name,
                    city=result.city,
                    country=result.country,
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


def _candidate_text(candidate: TripCandidatePlace) -> str:
    return f"{candidate.name} {candidate.category} {candidate.review_summary or ''} {candidate.why_selected}".lower()


def _candidate_has_any(candidate: TripCandidatePlace, terms: list[str]) -> bool:
    text = _candidate_text(candidate)
    return any(term in text for term in terms)


def _is_food_candidate(candidate: TripCandidatePlace) -> bool:
    return _candidate_has_any(candidate, ["food", "dining", "cuisine", "market", "restaurant", "bites"])


def _is_culture_candidate(candidate: TripCandidatePlace) -> bool:
    return _candidate_has_any(candidate, ["culture", "heritage", "history", "museum", "temple", "shrine"])


def _is_evening_candidate(candidate: TripCandidatePlace) -> bool:
    return _candidate_has_any(candidate, ["ambience", "atmosphere", "nightlife", "bar", "lanes", "evening", "romantic"])


def _is_relaxed_candidate(candidate: TripCandidatePlace) -> bool:
    return _candidate_has_any(candidate, ["calm", "walkable", "garden", "scenic", "relaxed", "river", "breathing room"])


def _cluster_transition_cost(from_cluster: str | None, to_cluster: str | None) -> float:
    if not from_cluster or not to_cluster:
        return 1.5
    if (from_cluster, to_cluster) in CLUSTER_TRAVEL_COSTS:
        return CLUSTER_TRAVEL_COSTS[(from_cluster, to_cluster)]
    if (to_cluster, from_cluster) in CLUSTER_TRAVEL_COSTS:
        return CLUSTER_TRAVEL_COSTS[(to_cluster, from_cluster)]
    return 3.0


def _clusters_are_coherent(cluster_a: str | None, cluster_b: str | None) -> bool:
    return _cluster_transition_cost(cluster_a, cluster_b) <= 2.0


def _cross_day_usage_penalty(candidate: TripCandidatePlace, usage_counts: dict[str, int], previous_day_ids: set[str]) -> float:
    usage_count = usage_counts.get(candidate.location_id, 0)
    penalty = usage_count * 8.0
    if candidate.location_id in previous_day_ids:
        penalty += 4.0
    return penalty


def _final_day_bonus(candidate: TripCandidatePlace, pace: str | None) -> float:
    if pace == "relaxed" and candidate.geo_cluster == "scenic_zone":
        return 3.5
    return 0.0


def _base_day_candidate_score(
    candidate: TripCandidatePlace,
    day_number: int,
    duration_days: int,
    pace: str | None,
    usage_counts: dict[str, int],
    previous_day_ids: set[str],
) -> float:
    score = candidate.score
    score -= _cross_day_usage_penalty(candidate, usage_counts, previous_day_ids)

    if day_number == 1 and candidate.geo_cluster == "central_core":
        score += 3.0
    if day_number == duration_days:
        score += _final_day_bonus(candidate, pace)
    if pace == "relaxed" and _is_relaxed_candidate(candidate):
        score += 1.5

    return score


def _choose_day_dominant_cluster(
    candidate_places: list[TripCandidatePlace],
    day_number: int,
    duration_days: int,
    pace: str | None,
    usage_counts: dict[str, int],
    previous_day_ids: set[str],
) -> str | None:
    if not candidate_places:
        return None

    ranked = sorted(
        candidate_places,
        key=lambda candidate: _base_day_candidate_score(
            candidate,
            day_number=day_number,
            duration_days=duration_days,
            pace=pace,
            usage_counts=usage_counts,
            previous_day_ids=previous_day_ids,
        ),
        reverse=True,
    )

    return ranked[0].geo_cluster if ranked else None


def _build_day_candidate_pool(
    day_number: int,
    duration_days: int,
    candidate_places: list[TripCandidatePlace],
    dominant_cluster: str | None,
    pace: str | None,
    usage_counts: dict[str, int],
    previous_day_ids: set[str],
) -> list[TripCandidatePlace]:
    if not candidate_places:
        return []

    scored: list[tuple[float, TripCandidatePlace]] = []

    for candidate in candidate_places:
        score = _base_day_candidate_score(
            candidate,
            day_number=day_number,
            duration_days=duration_days,
            pace=pace,
            usage_counts=usage_counts,
            previous_day_ids=previous_day_ids,
        )

        if dominant_cluster and candidate.geo_cluster == dominant_cluster:
            score += 4.0
        elif dominant_cluster and _clusters_are_coherent(candidate.geo_cluster, dominant_cluster):
            score += 1.5

        if pace == "relaxed" and candidate.geo_cluster == "scenic_zone":
            score += 1.0

        scored.append((score, candidate))

    scored.sort(key=lambda item: item[0], reverse=True)

    pool: list[TripCandidatePlace] = []
    seen_ids: set[str] = set()
    reused_from_previous_day = 0
    max_previous_day_reuse = 1 if previous_day_ids else 0

    for _, candidate in scored:
        if candidate.location_id in seen_ids:
            continue

        is_previous_day_candidate = candidate.location_id in previous_day_ids

        if is_previous_day_candidate and reused_from_previous_day >= max_previous_day_reuse:
            continue

        pool.append(candidate)
        seen_ids.add(candidate.location_id)

        if is_previous_day_candidate:
            reused_from_previous_day += 1

        if len(pool) >= 5:
            break

    if len(pool) < 5:
        for _, candidate in scored:
            if candidate.location_id in seen_ids:
                continue
            pool.append(candidate)
            seen_ids.add(candidate.location_id)
            if len(pool) >= 5:
                break

    return pool


def _build_day_fallbacks(
    assigned_candidates: list[TripCandidatePlace],
    all_candidates: list[TripCandidatePlace],
) -> tuple[list[str], list[str]]:
    assigned_ids = {candidate.location_id for candidate in assigned_candidates}
    fallback_candidates = [candidate for candidate in all_candidates if candidate.location_id not in assigned_ids][:3]

    return (
        [candidate.location_id for candidate in fallback_candidates],
        [candidate.name for candidate in fallback_candidates],
    )


def _slot_summary(
    slot_type: str,
    destination: str,
    interests: list[str],
    pace: str | None,
    place_name: str | None,
) -> str:
    interests_text = ", ".join(interests[:2]) if interests else "local discovery"
    anchor = place_name or destination

    if slot_type == "morning":
        return f"Start with {anchor} and ease into the day around {interests_text}."
    if slot_type == "lunch":
        return f"Keep lunch anchored around {anchor}, with a strong lean toward {interests_text}."
    if slot_type == "afternoon":
        if pace == "fast":
            return f"Use the afternoon for broader coverage around {anchor} while keeping momentum high."
        if pace == "relaxed":
            return f"Keep the afternoon slower and more focused around {anchor}."
        return f"Use the afternoon for balanced exploration centered on {anchor}."
    return f"Close the day with {anchor} and leave room for flexible evening choices."


def _slot_rationale(
    slot_type: str,
    candidate: TripCandidatePlace | None,
    day_title: str,
    mode: str = "default",
) -> str:
    if candidate is None:
        return f"This {slot_type} slot is intentionally flexible within {day_title.lower()}."

    if mode == "replaced":
        return (
            f"{candidate.name} now anchors the {slot_type} slot because it ranked better for this edit request "
            f"while staying aligned with {day_title.lower()}."
        )

    if mode == "retained_best_fit":
        return (
            f"{candidate.name} remains in the {slot_type} slot because no stronger alternative outranked it "
            f"for this edit request while staying aligned with {day_title.lower()}."
        )

    return (
        f"{candidate.name} was assigned to the {slot_type} slot because it fits the tone of "
        f"{day_title.lower()} and remains one of the stronger available candidates."
    )


def _slot_specialization_score(
    slot_type: str,
    candidate: TripCandidatePlace,
    pace: str | None,
    interests: list[str],
) -> float:
    score = candidate.score

    if slot_type == "morning":
        if _is_culture_candidate(candidate) or _is_relaxed_candidate(candidate):
            score += 4.0
        if candidate.geo_cluster == "heritage_core":
            score += 1.5
    elif slot_type == "lunch":
        if _is_food_candidate(candidate):
            score += 8.0
        if candidate.geo_cluster in {"central_core", "urban_core"}:
            score += 1.5
    elif slot_type == "afternoon":
        if _is_culture_candidate(candidate) or _is_relaxed_candidate(candidate):
            score += 4.0
        if candidate.geo_cluster == "scenic_zone":
            score += 1.5
    elif slot_type == "evening":
        if _is_evening_candidate(candidate):
            score += 7.0
        if candidate.geo_cluster in {"urban_core", "heritage_core"}:
            score += 2.0

    if pace == "relaxed" and _is_relaxed_candidate(candidate):
        score += 2.0
    if pace == "fast" and _is_evening_candidate(candidate):
        score += 1.0

    for interest in interests[:2]:
        if interest in _candidate_text(candidate):
            score += 1.0

    return score


def _same_day_usage_penalty(candidate: TripCandidatePlace, slot_usage_counts: dict[str, int]) -> float:
    usage_count = slot_usage_counts.get(candidate.location_id, 0)
    return usage_count * 12.0


def _route_continuity_bonus(
    slot_type: str,
    candidate: TripCandidatePlace,
    dominant_cluster: str | None,
    previous_candidate: TripCandidatePlace | None,
    pace: str | None,
) -> float:
    bonus = 0.0

    if dominant_cluster and candidate.geo_cluster == dominant_cluster:
        bonus += 3.5
    elif dominant_cluster and _clusters_are_coherent(candidate.geo_cluster, dominant_cluster):
        bonus += 1.5

    if previous_candidate is not None:
        transition_cost = _cluster_transition_cost(previous_candidate.geo_cluster, candidate.geo_cluster)
        if transition_cost == 0.0:
            bonus += 2.5
        elif transition_cost <= 1.5:
            bonus += 1.5

    if slot_type == "evening" and candidate.geo_cluster in {"urban_core", "heritage_core"}:
        bonus += 1.0

    if slot_type == "afternoon" and pace == "relaxed" and candidate.geo_cluster == "scenic_zone":
        bonus += 1.0

    return bonus


def _travel_friction_penalty(
    candidate: TripCandidatePlace,
    previous_candidate: TripCandidatePlace | None,
    pace: str | None,
) -> float:
    if previous_candidate is None:
        return 0.0

    transition_cost = _cluster_transition_cost(previous_candidate.geo_cluster, candidate.geo_cluster)
    penalty = transition_cost * 2.5

    if previous_candidate.location_id == candidate.location_id:
        penalty += 6.0

    if pace == "relaxed" and transition_cost >= 3.0:
        penalty += 2.0

    return penalty


def _movement_note(
    candidate: TripCandidatePlace | None,
    previous_candidate: TripCandidatePlace | None,
) -> str | None:
    if candidate is None:
        return None
    if previous_candidate is None:
        return f"Starts the day with a natural opening in {candidate.geo_cluster or 'the core area'}."

    cost = _cluster_transition_cost(previous_candidate.geo_cluster, candidate.geo_cluster)
    if cost == 0.0:
        return f"Keeps movement light by staying within {candidate.geo_cluster or 'the same cluster'}."
    if cost <= 1.5:
        return f"Maintains a fairly easy transition from {previous_candidate.name} into a nearby cluster."
    if cost <= 2.5:
        return f"Accepts a moderate transfer from {previous_candidate.name} to improve slot fit."
    return f"Takes a longer transfer from {previous_candidate.name} because the slot fit is materially stronger."


def _continuity_note(
    candidate: TripCandidatePlace | None,
    dominant_cluster: str | None,
) -> str | None:
    if candidate is None:
        return None
    if not dominant_cluster:
        return None
    if candidate.geo_cluster == dominant_cluster:
        return f"Supports the day’s main continuity around {dominant_cluster}."
    if _clusters_are_coherent(candidate.geo_cluster, dominant_cluster):
        return f"Works as a nearby extension from the day’s {dominant_cluster} anchor."
    return f"Acts as a deliberate detour away from the day’s {dominant_cluster} anchor."


def _candidate_lookup(candidate_places: list[TripCandidatePlace]) -> dict[str, TripCandidatePlace]:
    return {candidate.location_id: candidate for candidate in candidate_places}


def _ordered_unique_candidates_from_slots(
    slots: list[TripSlotAssignment],
    candidate_places: list[TripCandidatePlace],
) -> list[TripCandidatePlace]:
    candidate_map = _candidate_lookup(candidate_places)
    ordered: list[TripCandidatePlace] = []
    seen_ids: set[str] = set()

    for slot in slots:
        if not slot.assigned_location_id:
            continue
        candidate = candidate_map.get(slot.assigned_location_id)
        if candidate is None:
            continue
        if candidate.location_id in seen_ids:
            continue
        ordered.append(candidate)
        seen_ids.add(candidate.location_id)

    return ordered


def _limit_cross_day_overlap(
    ordered_candidates: list[TripCandidatePlace],
    previous_day_ids: set[str],
    max_overlap: int = 1,
) -> list[TripCandidatePlace]:
    if not ordered_candidates or not previous_day_ids:
        return ordered_candidates

    kept: list[TripCandidatePlace] = []
    repeated_count = 0

    for candidate in ordered_candidates:
        is_repeat = candidate.location_id in previous_day_ids

        if is_repeat and repeated_count >= max_overlap:
            continue

        kept.append(candidate)

        if is_repeat:
            repeated_count += 1

    return kept


def _best_non_repeated_candidate_for_slot(
    slot_type: str,
    candidate_places: list[TripCandidatePlace],
    previous_day_ids: set[str],
    already_used_ids: set[str],
    dominant_cluster: str | None,
    previous_candidate: TripCandidatePlace | None,
    pace: str | None,
    interests: list[str],
) -> TripCandidatePlace | None:
    strict_pool = [
        candidate
        for candidate in candidate_places
        if candidate.location_id not in previous_day_ids and candidate.location_id not in already_used_ids
    ]

    relaxed_pool = [
        candidate
        for candidate in candidate_places
        if candidate.location_id not in previous_day_ids
    ]

    fallback_pool = [
        candidate
        for candidate in candidate_places
        if candidate.location_id not in already_used_ids
    ]

    pool = strict_pool or relaxed_pool or fallback_pool
    if not pool:
        return None

    ranked = sorted(
        pool,
        key=lambda candidate: (
            _slot_specialization_score(slot_type, candidate, pace, interests)
            + _route_continuity_bonus(slot_type, candidate, dominant_cluster, previous_candidate, pace)
            - _travel_friction_penalty(candidate, previous_candidate, pace)
        ),
        reverse=True,
    )

    return ranked[0] if ranked else None


def _build_slot_alternatives(
    slot_type: str,
    current_candidate: TripCandidatePlace | None,
    candidate_places: list[TripCandidatePlace],
    dominant_cluster: str | None,
    previous_candidate: TripCandidatePlace | None,
    pace: str | None,
    interests: list[str],
    exclude_ids: set[str],
    max_items: int = 3,
) -> list[TripAlternativeSuggestion]:
    alternatives: list[tuple[float, TripCandidatePlace]] = []

    for candidate in candidate_places:
        if current_candidate is not None and candidate.location_id == current_candidate.location_id:
            continue
        if candidate.location_id in exclude_ids:
            continue

        score = _slot_specialization_score(slot_type, candidate, pace, interests)
        score += _route_continuity_bonus(slot_type, candidate, dominant_cluster, previous_candidate, pace)
        score -= _travel_friction_penalty(candidate, previous_candidate, pace)

        alternatives.append((score, candidate))

    alternatives.sort(key=lambda item: item[0], reverse=True)

    return [
        TripAlternativeSuggestion(
            location_id=candidate.location_id,
            name=candidate.name,
            city=candidate.city,
            country=candidate.country,
            category=candidate.category,
            score=round(score, 1),
            why_alternative=(
                f"A viable {slot_type} alternative that preserves a similar pacing and route-coherence profile."
            ),
            geo_cluster=candidate.geo_cluster,
        )
        for score, candidate in alternatives[:max_items]
    ]


def _enforce_cross_day_overlap_cap_on_slots(
    slots: list[TripSlotAssignment],
    candidate_places: list[TripCandidatePlace],
    previous_day_ids: set[str],
    max_overlap: int,
    day_title: str,
    destination: str,
    interests: list[str],
    pace: str | None,
    dominant_cluster: str | None,
) -> list[TripSlotAssignment]:
    if not previous_day_ids or not slots:
        return slots

    candidate_map = _candidate_lookup(candidate_places)
    repeat_count = 0
    already_used_ids: set[str] = set()
    previous_candidate: TripCandidatePlace | None = None

    for slot in slots:
        current_candidate = (
            candidate_map.get(slot.assigned_location_id)
            if slot.assigned_location_id
            else None
        )

        is_repeat = (
            current_candidate is not None
            and current_candidate.location_id in previous_day_ids
        )

        if is_repeat and repeat_count >= max_overlap:
            replacement_candidate = _best_non_repeated_candidate_for_slot(
                slot_type=slot.slot_type,
                candidate_places=candidate_places,
                previous_day_ids=previous_day_ids,
                already_used_ids=already_used_ids,
                dominant_cluster=dominant_cluster,
                previous_candidate=previous_candidate,
                pace=pace,
                interests=interests,
            )

            if replacement_candidate is not None:
                current_candidate = replacement_candidate
                slot.assigned_location_id = replacement_candidate.location_id
                slot.assigned_place_name = replacement_candidate.name
                slot.rationale = (
                    f"{replacement_candidate.name} was selected to keep {day_title.lower()} "
                    f"more distinct from the previous day while preserving day coherence."
                )

            slot.summary = _slot_summary(
                slot_type=slot.slot_type,
                destination=destination,
                interests=interests,
                pace=pace,
                place_name=current_candidate.name if current_candidate else None,
            )
            slot.continuity_note = _continuity_note(current_candidate, dominant_cluster)
            slot.movement_note = _movement_note(current_candidate, previous_candidate)

        if current_candidate is not None:
            if current_candidate.location_id in previous_day_ids and repeat_count < max_overlap:
                repeat_count += 1
            already_used_ids.add(current_candidate.location_id)
            previous_candidate = current_candidate

    return slots


def _assign_slots_for_day(
    day_pool: list[TripCandidatePlace],
    fallback_candidates: list[TripCandidatePlace],
    pace: str | None,
    interests: list[str],
    dominant_cluster: str | None,
) -> list[TripCandidatePlace | None]:
    pool: list[TripCandidatePlace] = list(day_pool)
    pool_ids = {candidate.location_id for candidate in pool}

    for fallback in fallback_candidates:
        if fallback.location_id not in pool_ids:
            pool.append(fallback)
            pool_ids.add(fallback.location_id)

    if not pool:
        return [None, None, None, None]

    slot_assignments: list[TripCandidatePlace | None] = []
    slot_usage_counts: dict[str, int] = {}
    previous_candidate: TripCandidatePlace | None = None

    for slot_type, _ in SLOT_SEQUENCE:
        ranked = sorted(
            pool,
            key=lambda candidate: (
                _slot_specialization_score(slot_type, candidate, pace, interests)
                + _route_continuity_bonus(slot_type, candidate, dominant_cluster, previous_candidate, pace)
                - _travel_friction_penalty(candidate, previous_candidate, pace)
                - _same_day_usage_penalty(candidate, slot_usage_counts)
            ),
            reverse=True,
        )

        chosen = ranked[0] if ranked else None
        slot_assignments.append(chosen)

        if chosen is not None:
            slot_usage_counts[chosen.location_id] = slot_usage_counts.get(chosen.location_id, 0) + 1
            previous_candidate = chosen

    return slot_assignments


def _build_day_rationale(
    day_title: str,
    pace: str | None,
    interests: list[str],
    assigned_candidates: list[TripCandidatePlace],
) -> str:
    pace_text = pace or "balanced"
    interests_text = ", ".join(interests[:2]) if interests else "general discovery"
    place_names = ", ".join(candidate.name for candidate in assigned_candidates[:2]) if assigned_candidates else "flexible candidates"

    return (
        f"{day_title} was structured with a {pace_text} pacing lens, leaning into {interests_text}, "
        f"with {place_names} shaping the slot-level flow."
    )


def _choose_day_cluster(assigned_candidates: list[TripCandidatePlace]) -> str | None:
    if not assigned_candidates:
        return None

    cluster_counts: dict[str, int] = {}
    for candidate in assigned_candidates:
        if not candidate.geo_cluster:
            continue
        cluster_counts[candidate.geo_cluster] = cluster_counts.get(candidate.geo_cluster, 0) + 1

    if not cluster_counts:
        return assigned_candidates[0].geo_cluster

    return max(cluster_counts.items(), key=lambda item: item[1])[0]


def _build_continuity_strategy(
    dominant_cluster: str | None,
    ordered_day_candidates: list[TripCandidatePlace],
) -> str | None:
    if not ordered_day_candidates:
        return None

    if dominant_cluster:
        unique_clusters = {
            candidate.geo_cluster
            for candidate in ordered_day_candidates
            if candidate.geo_cluster is not None
        }
        if len(unique_clusters) <= 1:
            return f"The day stays tightly anchored in {dominant_cluster} for stronger route coherence."
        return f"The day is anchored in {dominant_cluster} with only nearby cluster deviations where slot fit improves."

    return "The day balances slot fit while trying to keep movement reasonably light."


def _build_day_slots(
    day_number: int,
    day_title: str,
    destination: str,
    interests: list[str],
    pace: str | None,
    day_pool: list[TripCandidatePlace],
    all_candidates: list[TripCandidatePlace],
    dominant_cluster: str | None,
) -> tuple[list[TripSlotAssignment], list[TripCandidatePlace]]:
    _ = day_number
    slots: list[TripSlotAssignment] = []

    fallback_candidate_ids, fallback_candidate_names = _build_day_fallbacks(day_pool, all_candidates)
    fallback_candidates = [candidate for candidate in all_candidates if candidate.location_id in set(fallback_candidate_ids)]

    ordered_slot_candidates = _assign_slots_for_day(
        day_pool=day_pool,
        fallback_candidates=fallback_candidates,
        pace=pace,
        interests=interests,
        dominant_cluster=dominant_cluster,
    )

    previous_candidate: TripCandidatePlace | None = None
    unique_assigned_candidates: list[TripCandidatePlace] = []
    seen_ids: set[str] = set()

    for (slot_type, label), candidate in zip(SLOT_SEQUENCE, ordered_slot_candidates, strict=False):
        alternatives = _build_slot_alternatives(
            slot_type=slot_type,
            current_candidate=candidate,
            candidate_places=all_candidates,
            dominant_cluster=dominant_cluster,
            previous_candidate=previous_candidate,
            pace=pace,
            interests=interests,
            exclude_ids=seen_ids,
        )

        slots.append(
            TripSlotAssignment(
                slot_type=slot_type,
                label=label,
                summary=_slot_summary(
                    slot_type=slot_type,
                    destination=destination,
                    interests=interests,
                    pace=pace,
                    place_name=candidate.name if candidate else None,
                ),
                assigned_place_name=candidate.name if candidate else None,
                assigned_location_id=candidate.location_id if candidate else None,
                rationale=_slot_rationale(
                    slot_type=slot_type,
                    candidate=candidate,
                    day_title=day_title,
                ),
                continuity_note=_continuity_note(candidate, dominant_cluster),
                movement_note=_movement_note(candidate, previous_candidate),
                alternatives=alternatives,
                fallback_candidate_ids=fallback_candidate_ids,
                fallback_candidate_names=fallback_candidate_names,
            )
        )

        if candidate is not None:
            previous_candidate = candidate
            if candidate.location_id not in seen_ids:
                unique_assigned_candidates.append(candidate)
                seen_ids.add(candidate.location_id)

    return slots, unique_assigned_candidates


def _persist_trip_snapshot(
    db: Session,
    record: TripPlanRecord,
    snapshot_reason: str,
) -> None:
    snapshots = (
        db.query(TravellerMemoryRecord)
        .filter(TravellerMemoryRecord.traveller_id == record.traveller_id)
        .filter(TravellerMemoryRecord.event_type == "itinerary_version_snapshot")
        .order_by(TravellerMemoryRecord.id.asc())
        .all()
    )

    version_number = 1 + sum(
        1
        for item in snapshots
        if str(item.payload.get("planning_session_id") or "") == record.planning_session_id
    )

    memory_record = TravellerMemoryRecord(
        traveller_id=record.traveller_id,
        event_type="itinerary_version_snapshot",
        source_surface=record.source_surface,
        payload={
            "planning_session_id": record.planning_session_id,
            "version_number": version_number,
            "snapshot_reason": snapshot_reason,
            "status": record.status,
            "destination": record.destination,
            "duration_days": record.duration_days,
            "group_type": record.group_type,
            "budget": record.budget,
            "pace_preference": record.pace_preference,
            "interests": list(record.interests or []),
            "candidate_places": list(record.candidate_places or []),
            "itinerary_skeleton": list(record.itinerary_skeleton or []),
        },
    )

    db.add(memory_record)
    db.commit()


def _get_record_or_raise(db: Session, planning_session_id: str) -> TripPlanRecord:
    record = (
        db.query(TripPlanRecord)
        .filter(TripPlanRecord.planning_session_id == planning_session_id)
        .first()
    )

    if record is None:
        raise ValueError(f"Trip plan not found for planning_session_id={planning_session_id}")

    return record


def _get_day_or_raise(itinerary_skeleton: list[TripDayPlan], day_number: int) -> TripDayPlan:
    for day in itinerary_skeleton:
        if day.day_number == day_number:
            return day
    raise RuntimeError(f"Day {day_number} not found in itinerary.")


def _get_slot_or_raise(day: TripDayPlan, slot_type: str) -> TripSlotAssignment:
    for slot in day.slots:
        if slot.slot_type == slot_type:
            return slot
    raise RuntimeError(f"Slot {slot_type} not found in day {day.day_number}.")


def _get_adjacent_slot_candidates(
    day: TripDayPlan,
    slot_type: str,
    candidate_places: list[TripCandidatePlace],
) -> tuple[TripCandidatePlace | None, TripCandidatePlace | None]:
    slot_index_lookup = {slot_name: index for index, (slot_name, _) in enumerate(SLOT_SEQUENCE)}
    candidate_map = _candidate_lookup(candidate_places)
    current_index = slot_index_lookup[slot_type]

    previous_candidate: TripCandidatePlace | None = None
    next_candidate: TripCandidatePlace | None = None

    if current_index > 0:
        previous_slot = day.slots[current_index - 1]
        if previous_slot.assigned_location_id:
            previous_candidate = candidate_map.get(previous_slot.assigned_location_id)

    if current_index < len(day.slots) - 1:
        next_slot = day.slots[current_index + 1]
        if next_slot.assigned_location_id:
            next_candidate = candidate_map.get(next_slot.assigned_location_id)

    return previous_candidate, next_candidate


def _replacement_interest_boost(candidate: TripCandidatePlace, mode: str, interests: list[str]) -> float:
    text = _candidate_text(candidate)
    score = 0.0

    if mode == "more_food" and ("food" in text or "dining" in text or "cuisine" in text or "market" in text):
        score += 6.0
    if mode == "more_culture" and ("culture" in text or "heritage" in text or "history" in text or "museum" in text or "temple" in text):
        score += 6.0
    if mode == "less_hectic":
        if "calm" in text or "relaxed" in text or "walkable" in text or "garden" in text or "scenic" in text:
            score += 5.0
        if "nightlife" in text or "late" in text or "energy" in text or "busy" in text:
            score -= 2.0

    for interest in interests[:2]:
        if interest in text:
            score += 1.5

    return score


def _slot_fit_bonus(slot_type: str, candidate: TripCandidatePlace, pace: str | None) -> float:
    text = _candidate_text(candidate)
    bonus = 0.0

    if slot_type == "morning":
        if "calm" in text or "walkable" in text or "culture" in text or "temple" in text or "garden" in text:
            bonus += 2.0
    elif slot_type == "lunch":
        if "food" in text or "dining" in text or "cuisine" in text or "market" in text:
            bonus += 4.0
    elif slot_type == "afternoon":
        if "culture" in text or "scenic" in text or "exploration" in text or "garden" in text:
            bonus += 2.5
    elif slot_type == "evening":
        if "ambience" in text or "nightlife" in text or "atmosphere" in text or "lanes" in text or "romantic" in text:
            bonus += 3.5

    if pace == "relaxed" and ("calm" in text or "walkable" in text or "relaxed" in text or "scenic" in text):
        bonus += 1.5
    if pace == "fast" and ("energy" in text or "broad" in text or "nightlife" in text):
        bonus += 1.0

    return bonus


def _day_overlap_penalty(candidate: TripCandidatePlace, day: TripDayPlan, slot_type: str) -> float:
    penalty = 0.0
    assigned_ids = {
        slot.assigned_location_id
        for slot in day.slots
        if slot.assigned_location_id and slot.slot_type != slot_type
    }
    if candidate.location_id in assigned_ids:
        penalty += 6.0
    return penalty


def _cluster_bonus(candidate: TripCandidatePlace, day: TripDayPlan) -> float:
    if not day.geo_cluster or not candidate.geo_cluster:
        return 0.0
    if candidate.geo_cluster == day.geo_cluster:
        return 3.0
    if _clusters_are_coherent(candidate.geo_cluster, day.geo_cluster):
        return 1.0
    return -2.0


def _replacement_route_penalty(
    candidate: TripCandidatePlace,
    previous_candidate: TripCandidatePlace | None,
    next_candidate: TripCandidatePlace | None,
    pace: str | None,
) -> float:
    penalty = _travel_friction_penalty(candidate, previous_candidate, pace)

    if next_candidate is not None:
        penalty += _travel_friction_penalty(next_candidate, candidate, pace)

    return penalty


def _rank_replacement_candidates(
    candidate_places: list[TripCandidatePlace],
    day: TripDayPlan,
    slot_type: str,
    parsed_constraints: ParsedTripConstraints,
    mode: str,
    current_assigned_location_id: str | None,
    preferred_location_id: str | None,
) -> list[tuple[float, float, TripCandidatePlace]]:
    scored: list[tuple[float, float, TripCandidatePlace]] = []
    previous_candidate, next_candidate = _get_adjacent_slot_candidates(day, slot_type, candidate_places)

    for candidate in candidate_places:
        replacement_score = candidate.score
        replacement_score += _slot_fit_bonus(slot_type, candidate, parsed_constraints.pace_preference)
        replacement_score += _replacement_interest_boost(
            candidate,
            mode,
            list(parsed_constraints.interests or []),
        )
        replacement_score += _cluster_bonus(candidate, day)
        replacement_score -= _day_overlap_penalty(candidate, day, slot_type)

        route_penalty = _replacement_route_penalty(
            candidate=candidate,
            previous_candidate=previous_candidate,
            next_candidate=next_candidate,
            pace=parsed_constraints.pace_preference,
        )
        replacement_score -= route_penalty

        if current_assigned_location_id and candidate.location_id == current_assigned_location_id:
            replacement_score += 1.0

        if preferred_location_id and candidate.location_id == preferred_location_id:
            replacement_score += 15.0

        scored.append((replacement_score, route_penalty, candidate))

    scored.sort(key=lambda item: item[0], reverse=True)
    return scored


def _refresh_slot_and_day_metadata(
    day: TripDayPlan,
    parsed_constraints: ParsedTripConstraints,
    candidate_places: list[TripCandidatePlace],
) -> TripDayPlan:
    candidate_lookup = _candidate_lookup(candidate_places)

    ordered_day_candidates: list[TripCandidatePlace] = []
    seen_ids: set[str] = set()

    for slot in day.slots:
        if slot.assigned_location_id and slot.assigned_location_id in candidate_lookup:
            current_candidate = candidate_lookup[slot.assigned_location_id]
            if current_candidate.location_id not in seen_ids:
                ordered_day_candidates.append(current_candidate)
                seen_ids.add(current_candidate.location_id)

    day.place_names = [candidate.name for candidate in ordered_day_candidates]
    day.candidate_location_ids = [candidate.location_id for candidate in ordered_day_candidates]
    day.fallback_candidate_ids, day.fallback_candidate_names = _build_day_fallbacks(ordered_day_candidates, candidate_places)
    day.geo_cluster = _choose_day_cluster(ordered_day_candidates)
    day.continuity_strategy = _build_continuity_strategy(
        dominant_cluster=day.geo_cluster,
        ordered_day_candidates=ordered_day_candidates,
    )

    previous_candidate: TripCandidatePlace | None = None
    for slot in day.slots:
        current_candidate = (
            candidate_lookup.get(slot.assigned_location_id)
            if slot.assigned_location_id
            else None
        )

        slot.summary = _slot_summary(
            slot_type=slot.slot_type,
            destination=parsed_constraints.destination or "the destination",
            interests=list(parsed_constraints.interests or []),
            pace=parsed_constraints.pace_preference,
            place_name=current_candidate.name if current_candidate else None,
        )
        slot.continuity_note = _continuity_note(current_candidate, day.geo_cluster)
        slot.movement_note = _movement_note(current_candidate, previous_candidate)
        slot.alternatives = _build_slot_alternatives(
            slot_type=slot.slot_type,
            current_candidate=current_candidate,
            candidate_places=candidate_places,
            dominant_cluster=day.geo_cluster,
            previous_candidate=previous_candidate,
            pace=parsed_constraints.pace_preference,
            interests=list(parsed_constraints.interests or []),
            exclude_ids={slot.assigned_location_id} if slot.assigned_location_id else set(),
        )
        slot.fallback_candidate_ids = list(day.fallback_candidate_ids)
        slot.fallback_candidate_names = list(day.fallback_candidate_names)

        if current_candidate is not None:
            previous_candidate = current_candidate

    day.day_rationale = _build_day_rationale(
        day_title=day.title,
        pace=parsed_constraints.pace_preference,
        interests=list(parsed_constraints.interests or []),
        assigned_candidates=ordered_day_candidates,
    )
    day.summary = _day_summary(
        day_number=day.day_number,
        total_days=parsed_constraints.duration_days or day.day_number,
        destination=parsed_constraints.destination or "the destination",
        interests=list(parsed_constraints.interests or []),
        pace=parsed_constraints.pace_preference,
        place_names=day.place_names,
    )

    return day


def _build_itinerary_skeleton(
    parsed_constraints: ParsedTripConstraints,
    candidate_places: list[TripCandidatePlace],
) -> list[TripDayPlan]:
    duration_days = parsed_constraints.duration_days or 0
    destination = parsed_constraints.destination or "the destination"
    interests = list(parsed_constraints.interests or [])
    pace = parsed_constraints.pace_preference

    skeleton: list[TripDayPlan] = []

    if duration_days <= 0:
        return skeleton

    usage_counts: dict[str, int] = {}
    previous_day_ids: set[str] = set()

    for day_number in range(1, duration_days + 1):
        dominant_cluster = _choose_day_dominant_cluster(
            candidate_places=candidate_places,
            day_number=day_number,
            duration_days=duration_days,
            pace=pace,
            usage_counts=usage_counts,
            previous_day_ids=previous_day_ids,
        )

        day_pool = _build_day_candidate_pool(
            day_number=day_number,
            duration_days=duration_days,
            candidate_places=candidate_places,
            dominant_cluster=dominant_cluster,
            pace=pace,
            usage_counts=usage_counts,
            previous_day_ids=previous_day_ids,
        )

        fallback_candidate_ids, fallback_candidate_names = _build_day_fallbacks(day_pool, candidate_places)
        day_title = _day_title(day_number, duration_days, pace)

        slots, ordered_day_candidates = _build_day_slots(
            day_number=day_number,
            day_title=day_title,
            destination=destination,
            interests=interests,
            pace=pace,
            day_pool=day_pool,
            all_candidates=candidate_places,
            dominant_cluster=dominant_cluster,
        )

        slots = _enforce_cross_day_overlap_cap_on_slots(
            slots=slots,
            candidate_places=candidate_places,
            previous_day_ids=previous_day_ids,
            max_overlap=1,
            day_title=day_title,
            destination=destination,
            interests=interests,
            pace=pace,
            dominant_cluster=dominant_cluster,
        )

        ordered_day_candidates = _ordered_unique_candidates_from_slots(
            slots=slots,
            candidate_places=candidate_places,
        )
        ordered_day_candidates = _limit_cross_day_overlap(
            ordered_candidates=ordered_day_candidates,
            previous_day_ids=previous_day_ids,
            max_overlap=1,
        )

        if ordered_day_candidates:
            fallback_candidate_ids, fallback_candidate_names = _build_day_fallbacks(
                ordered_day_candidates,
                candidate_places,
            )
        for slot in slots:
            slot.fallback_candidate_ids = list(fallback_candidate_ids)
            slot.fallback_candidate_names = list(fallback_candidate_names)

        place_names = [candidate.name for candidate in ordered_day_candidates]
        candidate_ids = [candidate.location_id for candidate in ordered_day_candidates]
        geo_cluster = _choose_day_cluster(ordered_day_candidates)

        skeleton.append(
            TripDayPlan(
                day_number=day_number,
                title=day_title,
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
                slots=slots,
                day_rationale=_build_day_rationale(
                    day_title=day_title,
                    pace=pace,
                    interests=interests,
                    assigned_candidates=ordered_day_candidates,
                ),
                continuity_strategy=_build_continuity_strategy(
                    dominant_cluster=geo_cluster or dominant_cluster,
                    ordered_day_candidates=ordered_day_candidates,
                ),
                fallback_candidate_ids=fallback_candidate_ids,
                fallback_candidate_names=fallback_candidate_names,
                geo_cluster=geo_cluster,
            )
        )

        for candidate_id in candidate_ids:
            usage_counts[candidate_id] = usage_counts.get(candidate_id, 0) + 1

        previous_day_ids = set(candidate_ids)

    return skeleton


def _parsed_constraints_to_json(parsed_constraints: ParsedTripConstraints | None) -> dict[str, object]:
    if parsed_constraints is None:
        return {}
    return parsed_constraints.model_dump()


def _candidate_places_to_json(candidate_places: list[TripCandidatePlace] | None) -> list[dict[str, object]]:
    if not candidate_places:
        return []
    return [item.model_dump() for item in candidate_places]


def _day_plans_to_json(day_plans: list[TripDayPlan] | None) -> list[dict[str, object]]:
    if not day_plans:
        return []
    return [item.model_dump() for item in day_plans]


def _build_saved_trip_response(record: SavedTripRecord) -> SavedTripSummaryResponse:
    parsed_constraints_payload = dict(record.current_parsed_constraints or {})
    candidate_places_payload = list(record.current_candidate_places or [])
    itinerary_skeleton_payload = list(record.current_itinerary_skeleton or [])
    itinerary_payload = list(record.current_itinerary or [])

    return SavedTripSummaryResponse(
        trip_id=record.trip_id,
        traveller_id=record.traveller_id,
        planning_session_id=record.planning_session_id,
        title=record.title,
        destination=record.destination,
        start_date=record.start_date,
        end_date=record.end_date,
        companions=record.companions,
        status=record.status,
        source_surface=record.source_surface,
        current_version_number=record.current_version_number or 0,
        selected_places_count=record.selected_places_count or 0,
        skipped_recommendations_count=record.skipped_recommendations_count or 0,
        replaced_slots_count=record.replaced_slots_count or 0,
        parsed_constraints=ParsedTripConstraints(**parsed_constraints_payload) if parsed_constraints_payload else ParsedTripConstraints(),
        candidate_places=[TripCandidatePlace(**item) for item in candidate_places_payload],
        itinerary=itinerary_payload,
        itinerary_skeleton=[TripDayPlan(**item) for item in itinerary_skeleton_payload],
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _build_trip_version_response(record: ItineraryVersionRecord) -> TripVersionResponse:
    parsed_constraints_payload = dict(record.parsed_constraints or {})
    candidate_places_payload = list(record.candidate_places or [])
    itinerary_skeleton_payload = list(record.itinerary_skeleton or [])
    itinerary_payload = list(record.itinerary or [])

    return TripVersionResponse(
        version_id=record.version_id,
        trip_id=record.trip_id,
        traveller_id=record.traveller_id,
        planning_session_id=record.planning_session_id,
        version_number=record.version_number,
        snapshot_reason=record.snapshot_reason,
        source_surface=record.source_surface,
        status=record.status,
        parsed_constraints=ParsedTripConstraints(**parsed_constraints_payload) if parsed_constraints_payload else ParsedTripConstraints(),
        candidate_places=[TripCandidatePlace(**item) for item in candidate_places_payload],
        itinerary=itinerary_payload,
        itinerary_skeleton=[TripDayPlan(**item) for item in itinerary_skeleton_payload],
        created_at=record.created_at,
    )


def _build_trip_signal_response(record: TripSignalRecord) -> TripSignalResponse:
    return TripSignalResponse(
        signal_id=record.signal_id,
        trip_id=record.trip_id,
        traveller_id=record.traveller_id,
        planning_session_id=record.planning_session_id,
        signal_type=record.signal_type,
        location_id=record.location_id,
        day_number=record.day_number,
        slot_type=record.slot_type,
        payload=dict(record.payload or {}),
        created_at=record.created_at,
    )


def _get_saved_trip_record_or_raise(db: Session, trip_id: str) -> SavedTripRecord:
    record = db.query(SavedTripRecord).filter(SavedTripRecord.trip_id == trip_id).first()
    if record is None:
        raise ValueError(f"Saved trip not found for trip_id={trip_id}")
    return record


def _build_version_record_from_saved_trip(
    saved_trip: SavedTripRecord,
    snapshot_reason: str,
) -> ItineraryVersionRecord:
    current_version_number = saved_trip.current_version_number or 0
    next_version_number = current_version_number + 1
    saved_trip.current_version_number = next_version_number

    return ItineraryVersionRecord(
        version_id=f"version_{uuid4().hex}",
        trip_id=saved_trip.trip_id,
        traveller_id=saved_trip.traveller_id,
        planning_session_id=saved_trip.planning_session_id,
        version_number=next_version_number,
        snapshot_reason=snapshot_reason,
        source_surface=saved_trip.source_surface,
        status=saved_trip.status,
        parsed_constraints=dict(saved_trip.current_parsed_constraints or {}),
        candidate_places=list(saved_trip.current_candidate_places or []),
        itinerary=list(saved_trip.current_itinerary or []),
        itinerary_skeleton=list(saved_trip.current_itinerary_skeleton or []),
    )


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


def update_trip_plan(
    db: Session,
    planning_session_id: str,
    payload: TripPlanUpdateRequest,
) -> TripPlanSummaryResponse:
    record = _get_record_or_raise(db, planning_session_id)

    if payload.destination is not None:
        record.destination = payload.destination
    if payload.duration_days is not None:
        record.duration_days = payload.duration_days
    if payload.group_type is not None:
        record.group_type = payload.group_type
    if payload.interests is not None:
        record.interests = _normalize_interests(list(payload.interests))
    if payload.pace_preference is not None:
        record.pace_preference = payload.pace_preference
    if payload.budget is not None:
        record.budget = payload.budget

    parsed_constraints = _build_parsed_constraints_from_record(record)
    record.missing_fields = _build_missing_fields(parsed_constraints)

    record.candidate_places = []
    record.itinerary_skeleton = []
    record.status = "draft"

    db.add(record)
    db.commit()
    db.refresh(record)

    return _build_summary_response(record)


def replace_trip_plan_slot(
    db: Session,
    planning_session_id: str,
    payload: TripSlotReplacementRequest,
) -> TripPlanSummaryResponse:
    record = _get_record_or_raise(db, planning_session_id)

    if record.status != "enriched":
        raise RuntimeError("Trip plan must be enriched before replacing a slot.")

    parsed_constraints = _build_parsed_constraints_from_record(record)
    candidate_places = [TripCandidatePlace(**item) for item in list(record.candidate_places or [])]
    itinerary_skeleton = [TripDayPlan(**item) for item in list(record.itinerary_skeleton or [])]

    if not candidate_places or not itinerary_skeleton:
        raise RuntimeError("Trip plan has no enriched itinerary to replace.")

    day = _get_day_or_raise(itinerary_skeleton, payload.day_number)
    slot = _get_slot_or_raise(day, payload.slot_type)

    current_assigned_location_id = slot.assigned_location_id

    ranked_candidates = _rank_replacement_candidates(
        candidate_places=candidate_places,
        day=day,
        slot_type=payload.slot_type,
        parsed_constraints=parsed_constraints,
        mode=payload.replacement_mode,
        current_assigned_location_id=current_assigned_location_id,
        preferred_location_id=payload.preferred_location_id,
    )

    if not ranked_candidates:
        raise RuntimeError("No replacement candidates available for this slot.")

    ranked_lookup = {candidate.location_id: (score, route_penalty) for score, route_penalty, candidate in ranked_candidates}
    current_score, current_route_penalty = ranked_lookup.get(current_assigned_location_id, (float("-inf"), float("inf")))

    stronger_alternative: TripCandidatePlace | None = None
    for score, route_penalty, candidate in ranked_candidates:
        if candidate.location_id == current_assigned_location_id:
            continue

        if score < current_score + 2.5:
            continue

        if route_penalty > current_route_penalty + 1.0:
            continue

        if _day_overlap_penalty(candidate, day, payload.slot_type) > 0:
            continue

        if day.geo_cluster and candidate.geo_cluster and not _clusters_are_coherent(candidate.geo_cluster, day.geo_cluster):
            continue

        stronger_alternative = candidate
        break

    if stronger_alternative is not None:
        chosen = stronger_alternative
        slot.rationale = _slot_rationale(
            slot_type=payload.slot_type,
            candidate=chosen,
            day_title=day.title,
            mode="replaced",
        )
    else:
        chosen = next(
            (candidate for _, _, candidate in ranked_candidates if candidate.location_id == current_assigned_location_id),
            None,
        )
        if chosen is None:
            raise RuntimeError("No replacement candidates available for this slot.")

        slot.rationale = _slot_rationale(
            slot_type=payload.slot_type,
            candidate=chosen,
            day_title=day.title,
            mode="retained_best_fit",
        )

    slot.assigned_place_name = chosen.name
    slot.assigned_location_id = chosen.location_id

    _refresh_slot_and_day_metadata(
        day=day,
        parsed_constraints=parsed_constraints,
        candidate_places=candidate_places,
    )

    record.itinerary_skeleton = [item.model_dump() for item in itinerary_skeleton]
    record.status = "enriched"
    record.missing_fields = []

    db.add(record)
    db.commit()
    db.refresh(record)
    _persist_trip_snapshot(db, record, snapshot_reason="slot_replaced")

    return _build_summary_response(record)


def get_trip_plan_summary(
    db: Session,
    planning_session_id: str,
) -> TripPlanSummaryResponse:
    record = _get_record_or_raise(db, planning_session_id)
    return _build_summary_response(record)


def enrich_trip_plan(
    db: Session,
    planning_session_id: str,
) -> TripPlanEnrichResponse:
    record = _get_record_or_raise(db, planning_session_id)

    parsed_constraints = _build_parsed_constraints_from_record(record)
    missing_fields = _build_missing_fields(parsed_constraints)

    if missing_fields:
        raise RuntimeError(
            "Trip plan is incomplete for enrichment. Missing fields: "
            + ", ".join(missing_fields)
        )

    candidate_places = _build_candidate_places(
        db=db,
        traveller_id=record.traveller_id,
        parsed_constraints=parsed_constraints,
    )
    itinerary_skeleton = _build_itinerary_skeleton(parsed_constraints, candidate_places)

    record.candidate_places = [item.model_dump() for item in candidate_places]
    record.itinerary_skeleton = [item.model_dump() for item in itinerary_skeleton]
    record.missing_fields = []
    record.status = "enriched"

    db.add(record)
    db.commit()
    db.refresh(record)
    _persist_trip_snapshot(db, record, snapshot_reason="enriched_plan_created")

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


def promote_trip_plan_to_saved_trip(
    db: Session,
    planning_session_id: str,
    payload: TripPromoteRequest,
) -> SavedTripSummaryResponse:
    plan_record = _get_record_or_raise(db, planning_session_id)

    parsed_constraints = _build_parsed_constraints_from_record(plan_record)
    candidate_places = [TripCandidatePlace(**item) for item in list(plan_record.candidate_places or [])]
    itinerary_skeleton = [TripDayPlan(**item) for item in list(plan_record.itinerary_skeleton or [])]

    destination = plan_record.destination or parsed_constraints.destination
    duration_days = parsed_constraints.duration_days or 0
    title = payload.title or f"{destination or 'Trip'} {duration_days}-day plan"

    saved_trip = SavedTripRecord(
        trip_id=f"trip_{uuid4().hex}",
        traveller_id=plan_record.traveller_id,
        planning_session_id=plan_record.planning_session_id,
        title=title,
        destination=destination,
        source_surface=payload.source_surface,
        status=payload.status,
        start_date=payload.start_date,
        end_date=payload.end_date,
        companions=payload.companions or plan_record.group_type,
        current_parsed_constraints=_parsed_constraints_to_json(parsed_constraints),
        current_candidate_places=_candidate_places_to_json(candidate_places),
        current_itinerary=_day_plans_to_json(itinerary_skeleton),
        current_itinerary_skeleton=_day_plans_to_json(itinerary_skeleton),
        current_version_number=0,
        selected_places_count=0,
        skipped_recommendations_count=0,
        replaced_slots_count=0,
    )

    version_record = _build_version_record_from_saved_trip(
        saved_trip=saved_trip,
        snapshot_reason="initial_promotion",
    )

    db.add(saved_trip)
    db.add(version_record)
    db.commit()
    db.refresh(saved_trip)

    return _build_saved_trip_response(saved_trip)


def list_saved_trips(
    db: Session,
    traveller_id: str,
    limit: int = 50,
) -> SavedTripListResponse:
    records = (
        db.query(SavedTripRecord)
        .filter(SavedTripRecord.traveller_id == traveller_id)
        .order_by(desc(SavedTripRecord.updated_at), desc(SavedTripRecord.id))
        .limit(limit)
        .all()
    )

    return SavedTripListResponse(
        traveller_id=traveller_id,
        total=len(records),
        items=[_build_saved_trip_response(record) for record in records],
    )


def get_saved_trip_summary(
    db: Session,
    trip_id: str,
) -> SavedTripSummaryResponse:
    record = _get_saved_trip_record_or_raise(db, trip_id)
    return _build_saved_trip_response(record)


def list_trip_versions(
    db: Session,
    trip_id: str,
    limit: int = 50,
) -> TripVersionListResponse:
    _get_saved_trip_record_or_raise(db, trip_id)

    records = (
        db.query(ItineraryVersionRecord)
        .filter(ItineraryVersionRecord.trip_id == trip_id)
        .order_by(desc(ItineraryVersionRecord.version_number), desc(ItineraryVersionRecord.id))
        .limit(limit)
        .all()
    )

    return TripVersionListResponse(
        trip_id=trip_id,
        total=len(records),
        items=[_build_trip_version_response(record) for record in records],
    )


def create_trip_version_snapshot(
    db: Session,
    trip_id: str,
    payload: TripVersionSnapshotRequest,
) -> TripVersionResponse:
    saved_trip = _get_saved_trip_record_or_raise(db, trip_id)

    if payload.parsed_constraints is not None:
        saved_trip.current_parsed_constraints = _parsed_constraints_to_json(payload.parsed_constraints)
    if payload.candidate_places is not None:
        saved_trip.current_candidate_places = _candidate_places_to_json(payload.candidate_places)
    if payload.itinerary is not None:
        saved_trip.current_itinerary = list(payload.itinerary)
    if payload.itinerary_skeleton is not None:
        saved_trip.current_itinerary_skeleton = _day_plans_to_json(payload.itinerary_skeleton)
    if payload.status is not None:
        saved_trip.status = payload.status

    version_record = _build_version_record_from_saved_trip(
        saved_trip=saved_trip,
        snapshot_reason=payload.snapshot_reason,
    )

    db.add(saved_trip)
    db.add(version_record)
    db.commit()
    db.refresh(version_record)

    return _build_trip_version_response(version_record)


def create_trip_signal(
    db: Session,
    trip_id: str,
    payload: TripSignalCreateRequest,
) -> TripSignalResponse:
    saved_trip = _get_saved_trip_record_or_raise(db, trip_id)

    signal_record = TripSignalRecord(
        signal_id=f"signal_{uuid4().hex}",
        trip_id=saved_trip.trip_id,
        traveller_id=saved_trip.traveller_id,
        planning_session_id=saved_trip.planning_session_id,
        signal_type=payload.signal_type,
        location_id=payload.location_id,
        day_number=payload.day_number,
        slot_type=payload.slot_type,
        payload=dict(payload.payload or {}),
    )

    current_selected_places_count = saved_trip.selected_places_count or 0
    current_skipped_recommendations_count = saved_trip.skipped_recommendations_count or 0
    current_replaced_slots_count = saved_trip.replaced_slots_count or 0

    if payload.signal_type == "selected_place":
        saved_trip.selected_places_count = current_selected_places_count + 1
    elif payload.signal_type == "skipped_recommendation":
        saved_trip.skipped_recommendations_count = current_skipped_recommendations_count + 1
    elif payload.signal_type == "replaced_slot":
        saved_trip.replaced_slots_count = current_replaced_slots_count + 1

    db.add(saved_trip)
    db.add(signal_record)
    db.commit()
    db.refresh(signal_record)

    return _build_trip_signal_response(signal_record)


def list_trip_signals(
    db: Session,
    trip_id: str,
    limit: int = 100,
) -> TripSignalListResponse:
    _get_saved_trip_record_or_raise(db, trip_id)

    records = (
        db.query(TripSignalRecord)
        .filter(TripSignalRecord.trip_id == trip_id)
        .order_by(desc(TripSignalRecord.created_at), desc(TripSignalRecord.id))
        .limit(limit)
        .all()
    )

    return TripSignalListResponse(
        trip_id=trip_id,
        total=len(records),
        items=[_build_trip_signal_response(record) for record in records],
    )