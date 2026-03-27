from __future__ import annotations

import math
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.services.photo_intelligence_service import enrich_place_payload_with_ranked_photos

from app.clients.google_places_client import GooglePlacesClient
from app.models.saved_trip import SavedTripRecord
from app.schemas.destination import (
    NearbyDiscoveryContext,
    NearbyDiscoveryRequest,
    NearbyDiscoveryResponse,
    NearbyPlaceRecommendation,
)
from app.services.persona_embedding_service import calculate_persona_relevance_score

google_places_client = GooglePlacesClient()
settings = get_settings()


def _haversine_meters(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> int:
    radius_earth_m = 6_371_000

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return int(round(radius_earth_m * c))


def _radius_sequence(
    starting_radius_meters: int,
    max_radius_meters: int,
    adaptive_radius: bool,
) -> list[int]:
    if not adaptive_radius:
        return [starting_radius_meters]

    candidates = [
        starting_radius_meters,
        max(1200, starting_radius_meters * 2),
        max(2000, starting_radius_meters * 3),
        max_radius_meters,
    ]
    deduped = sorted({radius for radius in candidates if radius <= max_radius_meters})
    if max_radius_meters not in deduped:
        deduped.append(max_radius_meters)
    return deduped


def _load_saved_trip_payload(
    db: Session,
    trip_id: str | None,
) -> dict[str, Any]:
    if not trip_id:
        return {}

    record = db.query(SavedTripRecord).filter(SavedTripRecord.trip_id == trip_id).first()
    if record is None:
        return {}

    return {
        "trip_id": record.trip_id,
        "traveller_id": record.traveller_id,
        "planning_session_id": record.planning_session_id,
        "destination": record.destination,
        "parsed_constraints": dict(record.current_parsed_constraints or {}),
        "candidate_places": list(record.current_candidate_places or []),
        "itinerary_skeleton": list(record.current_itinerary_skeleton or []),
    }


def _get_current_day_slot(
    saved_trip: dict[str, Any],
    current_day_number: int | None,
    current_slot_type: str | None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    if not current_day_number or not current_slot_type:
        return None, None

    itinerary = list(saved_trip.get("itinerary_skeleton") or [])
    for day in itinerary:
        if day.get("day_number") != current_day_number:
            continue

        for slot in list(day.get("slots") or []):
            if slot.get("slot_type") == current_slot_type:
                return day, slot

        return day, None

    return None, None


def _blocked_ids_from_context(context: NearbyDiscoveryContext) -> set[str]:
    blocked = set(context.exclude_location_ids)
    blocked.update(context.rejected_location_ids)
    blocked.update(context.closed_location_ids)
    blocked.update(context.unavailable_location_ids)

    recent_signals = list(context.context_payload.get("recent_signals") or [])
    for signal in recent_signals:
        signal_type = str(signal.get("signal_type") or "")
        if signal_type in {
            "nearby_rejected",
            "place_closed",
            "place_unavailable",
            "skipped_recommendation",
            "gem_skipped",
        } and signal.get("location_id"):
            blocked.add(str(signal["location_id"]))

    return blocked


def _build_nearby_embedding_text(
    place: dict[str, Any],
    payload: NearbyDiscoveryRequest,
    context: NearbyDiscoveryContext,
) -> str:
    interests_text = ", ".join(payload.interests) if payload.interests else "general exploration"
    traveller_text = payload.traveller_type or "general traveller"

    return (
        f"query={payload.query or context.intent_hint or 'nearby discovery'}; "
        f"name={place.get('name') or 'unknown'}; "
        f"city={place.get('city') or payload.city or context.current_city or 'unknown'}; "
        f"country={place.get('country') or payload.country or context.current_country or 'unknown'}; "
        f"category={place.get('category') or 'unknown'}; "
        f"traveller_type={traveller_text}; "
        f"interests={interests_text}; "
        f"budget={payload.budget}; "
        f"slot={context.current_slot_type or 'unknown'}; "
        f"intent_hint={context.intent_hint or 'unknown'}; "
        f"rating={place.get('rating') or 0}; "
        f"review_count={place.get('review_count') or 0}"
    )


def _budget_bonus(
    budget: str,
    price_level: str | None,
) -> tuple[float, list[str]]:
    budget = budget.lower().strip()
    price_level = (price_level or "").lower().strip()

    if not price_level:
        return 0.0, []

    matrix: dict[str, dict[str, float]] = {
        "budget": {"budget": 5.0, "midrange": 1.5, "luxury": -4.0},
        "midrange": {"budget": 2.0, "midrange": 5.0, "luxury": -1.0},
        "luxury": {"budget": -1.0, "midrange": 2.0, "luxury": 5.0},
    }

    score = matrix.get(budget, {}).get(price_level, 0.0)
    if score > 0:
        return score, [f"fits your {budget} budget lens"]
    if score < 0:
        return score, [f"looks less aligned with your {budget} budget lens"]
    return 0.0, []


def _distance_bonus(
    distance_meters: int,
    transport_mode: str,
) -> tuple[float, list[str], bool]:
    transport_mode = transport_mode.lower().strip()
    walking_friendly = distance_meters <= 1600

    if transport_mode == "walk":
        if distance_meters <= 800:
            return 10.0, ["is very close for a walk"], True
        if distance_meters <= 1600:
            return 7.0, ["stays within a comfortable walking range"], True
        if distance_meters <= 2400:
            return 2.5, ["is still reachable on foot if you do not mind a longer walk"], False
        return -5.0, ["is a bit far for a walking-first option"], False

    if transport_mode == "transit":
        if distance_meters <= 1500:
            return 6.0, ["is easy to reach from where you are"], walking_friendly
        if distance_meters <= 3000:
            return 3.0, ["is still manageable with a short transfer"], walking_friendly
        return -2.0, ["needs a longer transfer"], walking_friendly

    if distance_meters <= 2500:
        return 5.0, ["is reasonably close"], walking_friendly
    if distance_meters <= 5000:
        return 2.0, ["is still workable from your current position"], walking_friendly
    return -1.0, ["is slightly farther out"], walking_friendly


def _time_bonus(
    open_now: bool | None,
    available_minutes: int | None,
    open_now_only: bool,
) -> tuple[float, list[str]]:
    if open_now is True:
        if available_minutes is not None and available_minutes <= 60:
            return 5.0, ["is open now and fits a tighter time window"]
        return 3.0, ["appears to be open now"]

    if open_now is False:
        if open_now_only:
            return -12.0, ["does not appear to be open right now"]
        return -4.0, ["may not be open right now"]

    return 0.0, []


def _intent_bonus(
    place: dict[str, Any],
    query: str | None,
    intent_hint: str | None,
    slot_type: str | None,
) -> tuple[float, list[str]]:
    text_blob = " ".join(
        [
            str(place.get("name") or ""),
            str(place.get("category") or ""),
            str(place.get("vibe_tags") or ""),
        ]
    ).lower()

    reasons: list[str] = []
    score = 0.0

    effective_query = (query or intent_hint or "").lower().strip()

    keyword_map: dict[str, list[str]] = {
        "food": ["food", "market", "restaurant", "dining", "cuisine", "coffee"],
        "culture": ["culture", "heritage", "museum", "temple", "historic", "old town"],
        "nature": ["park", "garden", "river", "nature", "scenic"],
        "nightlife": ["bar", "nightlife", "music", "late", "cocktail"],
        "coffee": ["coffee", "cafe", "espresso", "bakery"],
        "shopping": ["shopping", "boutique", "market", "stores"],
    }

    for intent, terms in keyword_map.items():
        if intent in effective_query and any(term in text_blob for term in terms):
            score += 6.0
            reasons.append(f"matches your live intent around {intent}")
            break

    if slot_type == "lunch" and any(term in text_blob for term in ["food", "market", "restaurant", "coffee"]):
        score += 3.5
        reasons.append("fits a lunch-time context")
    elif slot_type == "evening" and any(term in text_blob for term in ["bar", "nightlife", "music", "ambience"]):
        score += 3.5
        reasons.append("fits an evening context")
    elif slot_type == "morning" and any(term in text_blob for term in ["cafe", "bakery", "garden", "heritage", "park"]):
        score += 2.5
        reasons.append("works well in a morning slot")
    elif slot_type == "afternoon" and any(term in text_blob for term in ["museum", "scenic", "market", "district"]):
        score += 2.0
        reasons.append("fits an afternoon exploration window")

    return score, reasons


def _slot_and_trip_bonus(
    place: dict[str, Any],
    saved_trip: dict[str, Any],
    context: NearbyDiscoveryContext,
) -> tuple[float, list[str]]:
    _, slot = _get_current_day_slot(
        saved_trip=saved_trip,
        current_day_number=context.current_day_number,
        current_slot_type=context.current_slot_type,
    )

    if slot is None:
        return 0.0, []

    location_id = str(place.get("location_id") or "")
    fallback_ids = {str(item) for item in list(slot.get("fallback_candidate_ids") or [])}
    assigned_id = str(slot.get("assigned_location_id") or "")

    score = 0.0
    reasons: list[str] = []

    if location_id and location_id in fallback_ids:
        score += 7.0
        reasons.append("already appears as a viable fallback for your active slot")

    if location_id and location_id == assigned_id:
        score += 5.0
        reasons.append("is already aligned with your active itinerary slot")

    return score, reasons


def _build_reason_text(reasons: list[str]) -> str:
    if not reasons:
        return "Looks like a strong nearby option based on fit, distance, and current trip context."
    return "Recommended because it " + "; ".join(reasons[:3]) + "."

def _attach_photos_to_nearby_recommendations(
    db: Session,
    *,
    items: list[NearbyPlaceRecommendation],
    traveller_id: str | None,
    traveller_type: str | None,
    interests: list[str],
    context: NearbyDiscoveryContext,
    limit: int,
) -> list[NearbyPlaceRecommendation]:
    context_tags = []
    if context.intent_hint:
        context_tags.append(context.intent_hint)
    if context.current_slot_type:
        context_tags.append(context.current_slot_type)

    enriched: list[NearbyPlaceRecommendation] = []
    for item in items:
        payload = enrich_place_payload_with_ranked_photos(
            db,
            payload=item.model_dump(mode="json"),
            traveller_id=traveller_id,
            traveller_type=traveller_type,
            interests=interests,
            context_tags=context_tags,
            limit=limit,
        )
        enriched.append(NearbyPlaceRecommendation(**payload))
    return enriched


def discover_context_aware_nearby_places(
    db: Session,
    payload: NearbyDiscoveryRequest,
) -> NearbyDiscoveryResponse:
    context = payload.context or NearbyDiscoveryContext()
    blocked_location_ids = _blocked_ids_from_context(context)

    saved_trip = dict(context.context_payload.get("saved_trip") or {})
    if not saved_trip:
        saved_trip = _load_saved_trip_payload(db, context.trip_id)

    radii = _radius_sequence(
        starting_radius_meters=payload.starting_radius_meters,
        max_radius_meters=payload.max_radius_meters,
        adaptive_radius=payload.adaptive_radius,
    )

    search_expansions: list[int] = []
    aggregated: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    radius_used = radii[-1]

    open_now_only = bool(
        context.open_now_only
        or (context.available_minutes is not None and context.available_minutes <= 60)
    )

    for radius in radii:
        search_expansions.append(radius)

        provider_items = google_places_client.search_nearby_places(
            latitude=payload.latitude,
            longitude=payload.longitude,
            city=payload.city or context.current_city,
            country=payload.country or context.current_country,
            query=payload.query or context.intent_hint,
            radius_meters=radius,
            limit=max(payload.limit * 3, 12),
            open_now_only=open_now_only,
        )

        for item in provider_items:
            location_id = str(item.get("location_id") or "")
            if not location_id or location_id in seen_ids or location_id in blocked_location_ids:
                continue
            seen_ids.add(location_id)
            aggregated.append(item)

        if len(aggregated) >= payload.limit:
            radius_used = radius
            break

    ranked_rows: list[tuple[float, dict[str, Any]]] = []

    for item in aggregated:
        item_lat = float(item.get("latitude") or 0.0)
        item_lon = float(item.get("longitude") or 0.0)
        distance_meters = _haversine_meters(payload.latitude, payload.longitude, item_lat, item_lon)

        if distance_meters > payload.max_radius_meters:
            continue

        transport_mode = context.transport_mode or "walk"

        score = float(item.get("rating") or 0.0) * 10.0
        reasons: list[str] = []

        distance_score, distance_reasons, walking_friendly = _distance_bonus(distance_meters, transport_mode)
        time_score, time_reasons = _time_bonus(
            open_now=item.get("open_now"),
            available_minutes=context.available_minutes,
            open_now_only=open_now_only,
        )
        budget_score, budget_reasons = _budget_bonus(
            budget=context.budget or payload.budget,
            price_level=item.get("price_level"),
        )
        intent_score, intent_reasons = _intent_bonus(
            place=item,
            query=payload.query,
            intent_hint=context.intent_hint,
            slot_type=context.current_slot_type,
        )
        trip_score, trip_reasons = _slot_and_trip_bonus(
            place=item,
            saved_trip=saved_trip,
            context=context,
        )

        score += distance_score + time_score + budget_score + intent_score + trip_score
        reasons.extend(distance_reasons)
        reasons.extend(time_reasons)
        reasons.extend(budget_reasons)
        reasons.extend(intent_reasons)
        reasons.extend(trip_reasons)

        persona_relevance_score: float | None = None
        if payload.traveller_id:
            persona_relevance_score = calculate_persona_relevance_score(
                db=db,
                traveller_id=payload.traveller_id,
                text=_build_nearby_embedding_text(item, payload, context),
            )
            score += (persona_relevance_score or 0.0) * 12.0
            if persona_relevance_score is not None and persona_relevance_score >= 0.72:
                reasons.append("shows a strong fit for this traveller persona")

        ranked_rows.append(
            (
                round(score, 1),
                {
                    "location_id": str(item.get("location_id") or ""),
                    "name": str(item.get("name") or ""),
                    "city": str(item.get("city") or payload.city or context.current_city or "Unknown"),
                    "country": str(item.get("country") or payload.country or context.current_country or "Unknown"),
                    "category": str(item.get("category") or "place"),
                    "rating": float(item.get("rating") or 0.0),
                    "review_count": int(item.get("review_count") or 0),
                    "distance_meters": distance_meters,
                    "walking_minutes": max(1, round(distance_meters / 80)) if transport_mode == "walk" else None,
                    "price_level": item.get("price_level"),
                    "open_now": item.get("open_now"),
                    "source": str(item.get("source") or "nearby"),
                    "live_score": round(score, 1),
                    "fit_reasons": reasons[:4],
                    "why_recommended": _build_reason_text(reasons),
                    "walking_friendly": walking_friendly,
                },
            )
        )

    ranked_rows.sort(key=lambda row: (row[0], row[1]["review_count"]), reverse=True)

    normalized = [
        NearbyPlaceRecommendation(**row)
        for _, row in ranked_rows
    ]

    recommendations = normalized[: payload.limit]

    if not recommendations:
        fallback_pool: list[NearbyPlaceRecommendation] = []
        seen_fallback_ids: set[str] = set()

        candidate_places = list(saved_trip.get("candidate_places") or [])

        for candidate in candidate_places:
            location_id = str(candidate.get("location_id") or "")
            if not location_id or location_id in blocked_location_ids or location_id in seen_fallback_ids:
                continue

            seen_fallback_ids.add(location_id)

            fallback_pool.append(
                NearbyPlaceRecommendation(
                    location_id=location_id,
                    name=str(candidate.get("name") or ""),
                    city=str(candidate.get("city") or payload.city or context.current_city or "Unknown"),
                    country=str(candidate.get("country") or payload.country or context.current_country or "Unknown"),
                    category=str(candidate.get("category") or "place"),
                    rating=float(candidate.get("rating") or 0.0),
                    review_count=int(candidate.get("review_count") or 0),
                    distance_meters=0,
                    walking_minutes=None,
                    price_level=None,
                    open_now=None,
                    source="trip_context_fallback",
                    live_score=round(float(candidate.get("score") or 0.0), 1),
                    fit_reasons=[
                        "reused from your current trip candidate pool",
                        "live nearby search returned no strong in-radius matches",
                    ],
                    why_recommended=(
                        "Recommended from your active trip context because live nearby retrieval "
                        "did not return enough in-radius options."
                    ),
                    walking_friendly=False,
                )
            )

        recommendations = fallback_pool[: payload.limit]

    selected_ids = {item.location_id for item in recommendations}

    walking_alternatives = [
        item
        for item in normalized
        if item.walking_friendly and item.location_id not in selected_ids
    ][:3]

    fallback_ids = selected_ids | {item.location_id for item in walking_alternatives}
    fallbacks = [
        item
        for item in normalized
        if item.location_id not in fallback_ids
    ][:3]

    if not fallbacks and len(recommendations) > 1:
        fallbacks = recommendations[1: min(len(recommendations), 4)]

    recommendations = _attach_photos_to_nearby_recommendations(
        db,
        items=recommendations,
        traveller_id=payload.traveller_id,
        traveller_type=payload.traveller_type,
        interests=payload.interests,
        context=context,
        limit=settings.photo_preview_limit,
    )
    walking_alternatives = _attach_photos_to_nearby_recommendations(
        db,
        items=walking_alternatives,
        traveller_id=payload.traveller_id,
        traveller_type=payload.traveller_type,
        interests=payload.interests,
        context=context,
        limit=settings.photo_preview_limit,
    )
    fallbacks = _attach_photos_to_nearby_recommendations(
        db,
        items=fallbacks,
        traveller_id=payload.traveller_id,
        traveller_type=payload.traveller_type,
        interests=payload.interests,
        context=context,
        limit=settings.photo_preview_limit,
    )

    return NearbyDiscoveryResponse(
        city=payload.city or context.current_city,
        country=payload.country or context.current_country,
        query=payload.query or context.intent_hint,
        total=len(recommendations),
        radius_used_meters=radius_used,
        search_expansions=search_expansions,
        blocked_location_ids=sorted(blocked_location_ids),
        recommendations=recommendations,
        walking_alternatives=walking_alternatives,
        fallbacks=fallbacks,
    )