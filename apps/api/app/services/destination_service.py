import json
import math
from collections.abc import Generator
from typing import Any

from sqlalchemy.orm import Session

from app.clients.google_places_client import GooglePlacesClient
from app.clients.tripadvisor_client import TripadvisorClient
from app.db.session import get_db_session
from app.models.location_relation import LocationRelationRecord
from app.models.place_embedding import PlaceEmbeddingRecord
from app.models.place_embedding import PlaceEmbeddingRecord
from app.schemas.destination import (
    DestinationAlternative,
    DestinationAreaCard,
    DestinationComparisonDimension,
    DestinationComparisonRequest,
    DestinationComparisonResponse,
    DestinationComparisonSide,
    DestinationGuideRequest,
    DestinationGuideResponse,
    DestinationPlaceIndexItem,
    DestinationPlaceIndexRequest,
    DestinationPlaceIndexResponse,
    DestinationReviewInsight,
    DestinationSearchRequest,
    DestinationSearchResponse,
    SimilarPlaceMatch,
    SimilarPlaceRequest,
    SimilarPlaceResponse,
)
from app.services.embedding_service import get_embedding
from app.services.persona_embedding_service import calculate_persona_relevance_score
from app.services.review_intelligence_service import analyze_review_bundle

tripadvisor_client = TripadvisorClient()
google_places_client = GooglePlacesClient()

COMPARISON_DIMENSIONS = [
    "vibe",
    "food_scene",
    "walkability",
    "value_for_money",
    "romance",
    "family_friendliness",
    "cultural_richness",
    "safety",
    "nightlife",
    "nature_and_scenery",
]

DESTINATION_PROFILES: dict[str, dict[str, float]] = {
    "kyoto": {
        "vibe": 9.2,
        "food_scene": 8.8,
        "walkability": 8.4,
        "value_for_money": 7.6,
        "romance": 8.9,
        "family_friendliness": 8.0,
        "cultural_richness": 9.8,
        "safety": 9.4,
        "nightlife": 6.1,
        "nature_and_scenery": 8.8,
    },
    "tokyo": {
        "vibe": 9.0,
        "food_scene": 9.6,
        "walkability": 8.7,
        "value_for_money": 7.4,
        "romance": 8.1,
        "family_friendliness": 8.2,
        "cultural_richness": 8.7,
        "safety": 9.2,
        "nightlife": 8.7,
        "nature_and_scenery": 6.9,
    },
    "lisbon": {
        "vibe": 8.8,
        "food_scene": 8.6,
        "walkability": 8.1,
        "value_for_money": 8.3,
        "romance": 8.7,
        "family_friendliness": 7.5,
        "cultural_richness": 8.1,
        "safety": 7.8,
        "nightlife": 8.5,
        "nature_and_scenery": 7.6,
    },
    "prague": {
        "vibe": 8.9,
        "food_scene": 7.8,
        "walkability": 9.0,
        "value_for_money": 8.4,
        "romance": 8.8,
        "family_friendliness": 7.6,
        "cultural_richness": 9.0,
        "safety": 8.3,
        "nightlife": 7.9,
        "nature_and_scenery": 7.1,
    },
    "budapest": {
        "vibe": 8.5,
        "food_scene": 8.0,
        "walkability": 8.2,
        "value_for_money": 9.0,
        "romance": 8.3,
        "family_friendliness": 7.1,
        "cultural_richness": 8.4,
        "safety": 7.5,
        "nightlife": 8.8,
        "nature_and_scenery": 7.4,
    },
}

BASE_DIMENSION_WEIGHTS: dict[str, float] = {
    "vibe": 1.0,
    "food_scene": 1.0,
    "walkability": 1.0,
    "value_for_money": 1.0,
    "romance": 1.0,
    "family_friendliness": 1.0,
    "cultural_richness": 1.0,
    "safety": 1.0,
    "nightlife": 1.0,
    "nature_and_scenery": 1.0,
}

TRAVELLER_TYPE_WEIGHT_BONUSES: dict[str, dict[str, float]] = {
    "solo": {
        "walkability": 0.6,
        "safety": 0.7,
        "vibe": 0.4,
    },
    "couple": {
        "romance": 1.0,
        "food_scene": 0.4,
        "vibe": 0.3,
    },
    "family": {
        "family_friendliness": 1.1,
        "safety": 0.6,
        "walkability": 0.2,
    },
    "friends": {
        "nightlife": 0.8,
        "value_for_money": 0.5,
        "vibe": 0.4,
    },
}

INTEREST_WEIGHT_BONUSES: dict[str, dict[str, float]] = {
    "food": {
        "food_scene": 1.1,
        "value_for_money": 0.2,
    },
    "culture": {
        "cultural_richness": 1.1,
        "walkability": 0.2,
    },
    "nature": {
        "nature_and_scenery": 1.2,
        "vibe": 0.2,
    },
    "nightlife": {
        "nightlife": 1.1,
        "vibe": 0.2,
    },
    "luxury": {
        "vibe": 0.4,
        "food_scene": 0.3,
        "romance": 0.2,
    },
    "adventure": {
        "nature_and_scenery": 0.7,
        "walkability": 0.2,
    },
    "wellness": {
        "nature_and_scenery": 0.5,
        "safety": 0.2,
    },
}


def _build_place_embedding_text(
    destination: str,
    place: Any,
    traveller_type: str | None,
    interests: list[str],
) -> str:
    interests_text = ", ".join(interests) if interests else "general exploration"
    traveller_text = traveller_type or "general traveller"

    return (
        f"destination={destination}; "
        f"name={place.name}; "
        f"city={place.city}; "
        f"country={place.country}; "
        f"category={place.category}; "
        f"traveller_type={traveller_text}; "
        f"interests={interests_text}; "
        f"rating={place.rating}; "
        f"review_count={place.review_count}"
    )


def _cosine_similarity(vector_a: list[float], vector_b: list[float]) -> float:
    if not vector_a or not vector_b or len(vector_a) != len(vector_b):
        return 0.0

    dot_product = sum(a * b for a, b in zip(vector_a, vector_b))
    magnitude_a = math.sqrt(sum(a * a for a in vector_a))
    magnitude_b = math.sqrt(sum(b * b for b in vector_b))

    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0

    return round(dot_product / (magnitude_a * magnitude_b), 4)

def _relation_id(source_location_id: str, target_location_id: str) -> str:
    return f"{source_location_id}::{target_location_id}"


def _relation_type_for_pair(source: dict[str, Any], target: dict[str, Any], similarity: float) -> str:
    same_city = source["city"].strip().lower() == target["city"].strip().lower()
    same_category = source["category"].strip().lower() == target["category"].strip().lower()

    if same_city and same_category:
        return "same_city_peer"
    if same_city:
        return "same_city_match"
    if similarity >= 0.93:
        return "high_similarity"
    if source["source_destination"].strip().lower() == target["source_destination"].strip().lower():
        return "same_destination_context"
    return "contextual_match"


def _persist_related_location_links(
    db: Session,
    source_destination: str,
    embedded_items: list[dict[str, Any]],
) -> None:
    if len(embedded_items) < 2:
        return

    for source in embedded_items:
        for target in embedded_items:
            if source["location_id"] == target["location_id"]:
                continue

            similarity = _cosine_similarity(source["embedding_vector"], target["embedding_vector"])
            same_city = source["city"].strip().lower() == target["city"].strip().lower()

            if not same_city and similarity < 0.55:
                continue

            relation_record = LocationRelationRecord(
                relation_id=_relation_id(source["location_id"], target["location_id"]),
                source_location_id=source["location_id"],
                source_name=source["name"],
                source_city=source["city"],
                source_country=source["country"],
                target_location_id=target["location_id"],
                target_name=target["name"],
                target_city=target["city"],
                target_country=target["country"],
                target_category=target["category"],
                relation_type=_relation_type_for_pair(source, target, similarity),
                relation_score=round(similarity * 100.0, 1),
                city_match=same_city,
                destination_context=source_destination,
                target_rating=float(target["rating"]),
                target_review_count=int(target["review_count"]),
                relation_metadata={
                    "embedding_similarity": similarity,
                    "source_destination": source_destination,
                },
            )
            db.merge(relation_record)


def persist_place_embeddings_and_relations(
    db: Session,
    destination: str,
    traveller_type: str | None,
    interests: list[str],
    results: list[Any],
) -> list[dict[str, Any]]:
    persisted_items: list[dict[str, Any]] = []

    for result in results:
        embedding_text = _build_place_embedding_text(
            destination=destination,
            place=result,
            traveller_type=traveller_type,
            interests=interests,
        )
        embedding = get_embedding(embedding_text)

        record = PlaceEmbeddingRecord(
            location_id=result.location_id,
            name=result.name,
            city=result.city,
            country=result.country,
            category=result.category,
            source_destination=destination,
            embedding_provider=embedding.provider,
            embedding_model=embedding.model,
            embedding_dimensions=embedding.dimensions,
            embedding_vector=embedding.vector,
            rating=result.rating,
            review_count=result.review_count,
        )

        db.merge(record)

        persisted_items.append(
            {
                "location_id": result.location_id,
                "name": result.name,
                "city": result.city,
                "country": result.country,
                "category": result.category,
                "source_destination": destination,
                "rating": result.rating,
                "review_count": result.review_count,
                "embedding_dimensions": embedding.dimensions,
                "embedding_vector": embedding.vector,
            }
        )

    db.commit()
    _persist_related_location_links(db, destination, persisted_items)
    db.commit()

    return persisted_items


def get_related_location_suggestions(
    db: Session,
    source_location_id: str,
    top_k: int = 3,
    city_filter: str | None = None,
    exclude_location_ids: set[str] | None = None,
    allowed_location_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    exclude_location_ids = exclude_location_ids or set()

    query = db.query(LocationRelationRecord).filter(
        LocationRelationRecord.source_location_id == source_location_id
    )
    if city_filter:
        query = query.filter(LocationRelationRecord.target_city == city_filter)

    rows = query.all()

    suggestions: list[dict[str, Any]] = []
    for row in rows:
        if row.target_location_id in exclude_location_ids:
            continue
        if allowed_location_ids is not None and row.target_location_id not in allowed_location_ids:
            continue

        suggestions.append(
            {
                "location_id": row.target_location_id,
                "name": row.target_name,
                "city": row.target_city,
                "country": row.target_country,
                "category": row.target_category,
                "score": round(float(row.relation_score), 1),
                "relation_type": row.relation_type,
                "source": "relation",
                "city_match": bool(row.city_match),
                "why_alternative": (
                    f"Related via {row.relation_type.replace('_', ' ')} signals"
                    + (f" within {city_filter}." if city_filter else ".")
                ),
                "why_similar": (
                    f"Related via {row.relation_type.replace('_', ' ')} signals"
                    + (f" within {city_filter}." if city_filter else ".")
                ),
                "review_count": int(row.target_review_count),
            }
        )

    suggestions.sort(
        key=lambda item: (item["score"], item["review_count"]),
        reverse=True,
    )
    return suggestions[:top_k]


def _build_profile_based_you_would_also_love(
    payload: DestinationGuideRequest,
    db: Session | None = None,
    existing_ids: set[str] | None = None,
) -> list[DestinationAlternative]:
    existing_ids = existing_ids or set()
    alternatives: list[DestinationAlternative] = []

    for candidate_destination in DESTINATION_PROFILES:
        if candidate_destination == payload.destination.strip().lower():
            continue

        search_results = tripadvisor_client.search_locations(
            query=candidate_destination.title(),
            traveller_type=payload.traveller_type,
            interests=payload.interests,
        )
        if not search_results:
            continue

        result = search_results[0]
        if result.location_id in existing_ids:
            continue

        match_score = _profile_similarity_score(
            source_destination=payload.destination,
            candidate_destination=result.name,
            traveller_type=payload.traveller_type,
            interests=payload.interests,
        )

        persona_relevance = _compute_persona_relevance_for_place(
            db=db,
            traveller_id=payload.traveller_id,
            destination=payload.destination,
            place=result,
            traveller_type=payload.traveller_type,
            interests=payload.interests,
        )

        if persona_relevance is not None:
            match_score = min(100.0, round(match_score + (persona_relevance * 12.0), 1))

        alternatives.append(
            DestinationAlternative(
                location_id=result.location_id,
                name=result.name,
                city=result.city,
                country=result.country,
                category=result.category,
                match_score=match_score,
                reason=(
                    f"A strong alternate if you want a trip with a comparable fit for "
                    f"{', '.join(payload.interests[:2]) if payload.interests else 'your stated travel style'}."
                ),
                source="profile",
                city_match=False,
            )
        )

    alternatives.sort(key=lambda item: item.match_score, reverse=True)
    return alternatives

def _base_destination_result_rank_score(result: Any) -> float:
    review_volume_bonus = min(float(result.review_count) / 5000.0, 1.0) * 5.0
    return round((float(result.rating) * 20.0) + review_volume_bonus, 4)


def _compute_persona_relevance_for_place(
    db: Session | None,
    traveller_id: str | None,
    destination: str,
    place: Any,
    traveller_type: str | None,
    interests: list[str],
) -> float | None:
    if db is None or not traveller_id:
        return None

    embedding_text = _build_place_embedding_text(
        destination=destination,
        place=place,
        traveller_type=traveller_type,
        interests=interests,
    )

    return calculate_persona_relevance_score(
        db=db,
        traveller_id=traveller_id,
        text=embedding_text,
    )


def _rerank_destination_results_with_persona(
    db: Session | None,
    traveller_id: str | None,
    destination: str,
    traveller_type: str | None,
    interests: list[str],
    results: list[Any],
) -> list[Any]:
    if db is None or not traveller_id or not results:
        return results

    scored_results: list[tuple[float, Any]] = []

    for result in results:
        persona_relevance = _compute_persona_relevance_for_place(
            db=db,
            traveller_id=traveller_id,
            destination=destination,
            place=result,
            traveller_type=traveller_type,
            interests=interests,
        )

        rank_score = _base_destination_result_rank_score(result)
        if persona_relevance is not None:
            rank_score += persona_relevance * 15.0

        scored_results.append((rank_score, result))

    scored_results.sort(key=lambda item: item[0], reverse=True)
    return [result for _, result in scored_results]


def _persona_bonus_for_destination_score(persona_relevance_score: float | None) -> float:
    if persona_relevance_score is None:
        return 0.0

    return round(persona_relevance_score * 0.75, 2)


def _build_area_card(area: str, destination: str) -> DestinationAreaCard:
    area_map = {
        "Gion": {
            "summary": f"A classic base in {destination} for heritage lanes, evening atmosphere, and traditional character.",
            "why_it_fits": "Best if you want charm, walkable evenings, and a strong sense of place.",
        },
        "Higashiyama": {
            "summary": f"One of the strongest parts of {destination} for temples, old streets, and slower cultural exploration.",
            "why_it_fits": "A better fit when culture and traditional character matter more than speed.",
        },
        "Arashiyama": {
            "summary": f"A scenic side of {destination} that works well for nature, riverfront walks, and a lighter-paced half day.",
            "why_it_fits": "Ideal if you want a softer, more spacious contrast to denser city exploration.",
        },
        "Alfama": {
            "summary": f"A character-rich area in {destination} known for old lanes, viewpoints, and local atmosphere.",
            "why_it_fits": "Great when you want city texture, walking, and a more historic base.",
        },
        "Bairro Alto": {
            "summary": f"A livelier part of {destination} with stronger evening energy and central access.",
            "why_it_fits": "A stronger choice if nightlife and late-evening energy matter.",
        },
        "Chiado": {
            "summary": f"A balanced base in {destination} for cafés, culture, and easy movement across the city.",
            "why_it_fits": "Works well when you want convenience without losing city character.",
        },
        "Old Town": {
            "summary": f"A central area in {destination} that gives fast access to major first-time highlights.",
            "why_it_fits": "Best when your priority is broad city coverage in limited time.",
        },
        "Mala Strana": {
            "summary": f"A more atmospheric side of {destination} with classic views and calmer streets.",
            "why_it_fits": "A good fit if you prefer charm and pacing over maximum sightseeing density.",
        },
        "Vinohrady": {
            "summary": f"A more local-feeling part of {destination} with a relaxed rhythm and neighborhood vibe.",
            "why_it_fits": "Better when you want a softer, more resident-like city experience.",
        },
    }

    mapped = area_map.get(
        area,
        {
            "summary": f"A strong area to explore within {destination}, with good character and access to key experiences.",
            "why_it_fits": "A balanced fit for the way this guide is structured.",
        },
    )

    return DestinationAreaCard(
        name=area,
        summary=mapped["summary"],
        why_it_fits=mapped["why_it_fits"],
        rating=4.7,
    )


def _build_review_insight(
    review_summary: str,
    review_signals: dict[str, str],
    authenticity: str | None,
) -> DestinationReviewInsight:
    standout = []

    for label, value in review_signals.items():
        if value == "positive":
            standout.append(label.replace("_", " "))

    overall_vibe = "Well-liked by travellers overall."
    lowered = review_summary.lower()

    if "consistently rate this place highly" in lowered:
        overall_vibe = "Travellers speak positively about the destination overall."
    elif "mixed" in lowered:
        overall_vibe = "Traveller sentiment is mixed, with some clear strengths."

    confidence = {
        "high": "High",
        "medium": "Medium",
        "low": "Low",
        None: "Unknown",
    }.get(authenticity, "Unknown")

    return DestinationReviewInsight(
        overall_vibe=overall_vibe,
        standout_themes=standout[:3],
        confidence=confidence,
        raw_summary=review_summary,
    )


def _get_destination_profile(destination: str) -> dict[str, float]:
    lowered = destination.strip().lower()
    if lowered in DESTINATION_PROFILES:
        return DESTINATION_PROFILES[lowered]

    return {
        "vibe": 7.5,
        "food_scene": 7.5,
        "walkability": 7.4,
        "value_for_money": 7.4,
        "romance": 7.3,
        "family_friendliness": 7.3,
        "cultural_richness": 7.5,
        "safety": 7.5,
        "nightlife": 7.2,
        "nature_and_scenery": 7.4,
    }


def _build_dimension_weights(traveller_type: str, interests: list[str]) -> dict[str, float]:
    weights = dict(BASE_DIMENSION_WEIGHTS)

    for dimension, bonus in TRAVELLER_TYPE_WEIGHT_BONUSES.get(traveller_type, {}).items():
        weights[dimension] = weights.get(dimension, 1.0) + bonus

    for interest in interests:
        for dimension, bonus in INTEREST_WEIGHT_BONUSES.get(interest, {}).items():
            weights[dimension] = weights.get(dimension, 1.0) + bonus

    return weights


def _weighted_destination_score(
    destination: str,
    traveller_type: str,
    interests: list[str],
    persona_relevance_score: float | None = None,
) -> float:
    profile = _get_destination_profile(destination)
    weights = _build_dimension_weights(traveller_type, interests)

    numerator = sum(profile[dimension] * weights[dimension] for dimension in COMPARISON_DIMENSIONS)
    denominator = sum(weights[dimension] for dimension in COMPARISON_DIMENSIONS)

    if denominator == 0:
        return 0.0

    base_score = round(numerator / denominator, 2)
    persona_bonus = _persona_bonus_for_destination_score(persona_relevance_score)

    return round(min(10.0, base_score + persona_bonus), 2)


def _dimension_note(destination: str, dimension: str, score: float) -> str:
    readable_dimension = dimension.replace("_", " ")

    if score >= 8.8:
        return f"{destination} is especially strong on {readable_dimension}."
    if score >= 8.0:
        return f"{destination} performs well on {readable_dimension}."
    if score >= 7.0:
        return f"{destination} is fairly balanced on {readable_dimension}."
    return f"{destination} is less differentiated on {readable_dimension}."


def _comparison_tagline(destination: str, traveller_type: str, interests: list[str]) -> str:
    interests_text = ", ".join(interests[:2]) if interests else "general city exploration"
    return f"A strong option for {traveller_type} travellers leaning toward {interests_text}."


def _comparison_best_for(destination: str, traveller_type: str, interests: list[str]) -> str:
    profile = _get_destination_profile(destination)
    top_dimension = max(COMPARISON_DIMENSIONS, key=lambda item: profile[item]).replace("_", " ")
    interests_text = ", ".join(interests[:2]) if interests else "balanced city trips"
    return f"{traveller_type.capitalize()} travellers who care about {top_dimension} and {interests_text}."


def _build_comparison_side(
    destination: str,
    traveller_type: str,
    interests: list[str],
    traveller_id: str | None = None,
) -> DestinationComparisonSide:
    search_results = tripadvisor_client.search_locations(
        query=destination,
        traveller_type=traveller_type,
        interests=interests,
    )
    primary = search_results[0]
    review_bundle = tripadvisor_client.get_destination_reviews(primary.name)
    review_analysis = analyze_review_bundle(
        location_id=str(review_bundle["location_id"]),
        location_name=str(review_bundle["location_name"]),
        reviews=list(review_bundle["reviews"]),
    )
    context = google_places_client.get_destination_context(primary.name)

    persona_relevance: float | None = None
    if traveller_id:
        db = get_db_session()
        try:
            persona_relevance = _compute_persona_relevance_for_place(
                db=db,
                traveller_id=traveller_id,
                destination=destination,
                place=primary,
                traveller_type=traveller_type,
                interests=interests,
            )
        finally:
            db.close()

    return DestinationComparisonSide(
        location_id=primary.location_id,
        name=primary.name,
        city=primary.city,
        country=primary.country,
        category=primary.category,
        tagline=_comparison_tagline(primary.name, traveller_type, interests),
        best_for=_comparison_best_for(primary.name, traveller_type, interests),
        review_summary=review_analysis.quick_verdict,
        review_authenticity=review_analysis.authenticity_label,
        suggested_areas=list(context["suggested_areas"]),
        weighted_score=_weighted_destination_score(
            primary.name,
            traveller_type,
            interests,
            persona_relevance_score=persona_relevance,
        ),
    )


def _winner_label(score_a: float, score_b: float) -> str:
    if abs(score_a - score_b) < 0.15:
        return "tie"
    return "destination_a" if score_a > score_b else "destination_b"


def _build_comparison_dimensions(
    destination_a: str,
    destination_b: str,
    traveller_type: str,
    interests: list[str],
) -> list[DestinationComparisonDimension]:
    profile_a = _get_destination_profile(destination_a)
    profile_b = _get_destination_profile(destination_b)
    weights = _build_dimension_weights(traveller_type, interests)

    dimensions: list[DestinationComparisonDimension] = []

    for dimension in COMPARISON_DIMENSIONS:
        score_a = round(profile_a[dimension], 1)
        score_b = round(profile_b[dimension], 1)

        dimensions.append(
            DestinationComparisonDimension(
                name=dimension.replace("_", " ").title(),
                weight=round(weights[dimension], 2),
                score_a=score_a,
                score_b=score_b,
                note_a=_dimension_note(destination_a, dimension, score_a),
                note_b=_dimension_note(destination_b, dimension, score_b),
                winner=_winner_label(score_a, score_b),
            )
        )

    return dimensions


def _build_comparison_verdict(
    side_a: DestinationComparisonSide,
    side_b: DestinationComparisonSide,
    traveller_type: str,
    interests: list[str],
) -> str:
    interests_text = ", ".join(interests[:2]) if interests else "general exploration"

    if side_a.weighted_score > side_b.weighted_score:
        return (
            f"{side_a.name} comes out ahead for this {traveller_type} planning context because its weighted profile "
            f"better aligns with {interests_text}, while {side_b.name} still remains a credible alternative."
        )

    if side_b.weighted_score > side_a.weighted_score:
        return (
            f"{side_b.name} comes out ahead for this {traveller_type} planning context because its weighted profile "
            f"better aligns with {interests_text}, while {side_a.name} still remains a credible alternative."
        )

    return (
        f"{side_a.name} and {side_b.name} land very close for this {traveller_type} planning context, so the better "
        f"choice depends on whether you want stronger fit on your top priorities or a different trip character."
    )


def _build_planning_recommendation(
    side_a: DestinationComparisonSide,
    side_b: DestinationComparisonSide,
    duration_days: int,
) -> str:
    better = side_a if side_a.weighted_score >= side_b.weighted_score else side_b
    other = side_b if better is side_a else side_a

    return (
        f"If you want to move directly into planning, start the itinerary workspace with {better.name} for the main plan. "
        f"Keep {other.name} as the backup comparison branch, especially if you later want an alternate {duration_days}-day version."
    )


def _profile_similarity_score(
    source_destination: str,
    candidate_destination: str,
    traveller_type: str,
    interests: list[str],
) -> float:
    source_profile = _get_destination_profile(source_destination)
    candidate_profile = _get_destination_profile(candidate_destination)
    weights = _build_dimension_weights(traveller_type, interests)

    total_weight = sum(weights.values())
    if total_weight == 0:
        return 0.0

    weighted_distance = 0.0
    for dimension in COMPARISON_DIMENSIONS:
        weighted_distance += abs(source_profile[dimension] - candidate_profile[dimension]) * weights[dimension]

    normalized_distance = weighted_distance / total_weight
    similarity = max(0.0, 100.0 - (normalized_distance * 12.0))
    return round(similarity, 1)


def _build_you_would_also_love(
    payload: DestinationGuideRequest,
) -> list[DestinationAlternative]:
    alternatives: list[DestinationAlternative] = []
    seen_ids: set[str] = set()

    db = get_db_session()
    try:
        source_results = tripadvisor_client.search_locations(
            query=payload.destination,
            traveller_type=payload.traveller_type,
            interests=payload.interests,
        )

        if source_results:
            persisted_items = persist_place_embeddings_and_relations(
                db=db,
                destination=payload.destination,
                traveller_type=payload.traveller_type,
                interests=payload.interests,
                results=list(source_results[:8]),
            )

            primary_item = persisted_items[0]
            relation_suggestions = get_related_location_suggestions(
                db=db,
                source_location_id=primary_item["location_id"],
                top_k=3,
                city_filter=primary_item["city"],
                exclude_location_ids={primary_item["location_id"]},
            )

            for suggestion in relation_suggestions:
                if suggestion["location_id"] in seen_ids:
                    continue
                seen_ids.add(suggestion["location_id"])

                alternatives.append(
                    DestinationAlternative(
                        location_id=suggestion["location_id"],
                        name=suggestion["name"],
                        city=suggestion["city"],
                        country=suggestion["country"],
                        category=suggestion["category"],
                        match_score=suggestion["score"],
                        reason=suggestion["why_alternative"],
                        source_location_id=primary_item["location_id"],
                        relation_type=suggestion["relation_type"],
                        source=suggestion["source"],
                        city_match=suggestion["city_match"],
                    )
                )

        profile_based = _build_profile_based_you_would_also_love(
            payload=payload,
            db=db,
            existing_ids=seen_ids,
        )
        for item in profile_based:
            if item.location_id in seen_ids:
                continue
            seen_ids.add(item.location_id)
            alternatives.append(item)

    finally:
        db.close()

    alternatives.sort(key=lambda item: item.match_score, reverse=True)
    return alternatives[:3]


def search_destinations(payload: DestinationSearchRequest) -> DestinationSearchResponse:
    results = tripadvisor_client.search_locations(
        query=payload.query,
        traveller_type=payload.traveller_type,
        interests=payload.interests,
    )

    if payload.traveller_id:
        db = get_db_session()
        try:
            results = _rerank_destination_results_with_persona(
                db=db,
                traveller_id=payload.traveller_id,
                destination=payload.query,
                traveller_type=payload.traveller_type,
                interests=payload.interests,
                results=list(results),
            )
        finally:
            db.close()

    normalized_results = [
        {
            "location_id": result.location_id,
            "name": result.name,
            "city": result.city,
            "country": result.country,
            "category": result.category,
            "rating": result.rating,
            "review_count": result.review_count,
        }
        for result in results
    ]

    return DestinationSearchResponse(
        query=payload.query,
        results=normalized_results,
    )


def index_destination_places(
    db: Session,
    payload: DestinationPlaceIndexRequest,
) -> DestinationPlaceIndexResponse:
    results = tripadvisor_client.search_locations(
        query=payload.destination,
        traveller_type=payload.traveller_type,
        interests=payload.interests,
    )

    persisted_items = persist_place_embeddings_and_relations(
        db=db,
        destination=payload.destination,
        traveller_type=payload.traveller_type,
        interests=payload.interests,
        results=list(results),
    )

    indexed_items = [
        DestinationPlaceIndexItem(
            location_id=item["location_id"],
            name=item["name"],
            city=item["city"],
            country=item["country"],
            category=item["category"],
            embedding_dimensions=item["embedding_dimensions"],
        )
        for item in persisted_items
    ]

    return DestinationPlaceIndexResponse(
        destination=payload.destination,
        indexed_count=len(indexed_items),
        items=indexed_items,
    )

def get_similar_places(
    db: Session,
    payload: SimilarPlaceRequest,
) -> SimilarPlaceResponse:
    source_record = db.get(PlaceEmbeddingRecord, payload.source_location_id)
    if source_record is None:
        return SimilarPlaceResponse(
            source_location_id=payload.source_location_id,
            city_filter_applied=payload.city_filter,
            matches=[],
        )

    related_matches = get_related_location_suggestions(
        db=db,
        source_location_id=payload.source_location_id,
        top_k=payload.top_k,
        city_filter=payload.city_filter,
        exclude_location_ids={payload.source_location_id},
    )

    normalized_matches: list[SimilarPlaceMatch] = [
        SimilarPlaceMatch(
            location_id=item["location_id"],
            name=item["name"],
            city=item["city"],
            country=item["country"],
            category=item["category"],
            similarity_score=round(item["score"] / 100.0, 4),
            why_similar=item["why_similar"],
            relation_type=item["relation_type"],
            source=item["source"],
            city_match=item["city_match"],
        )
        for item in related_matches
    ]

    if len(normalized_matches) < payload.top_k:
        query = db.query(PlaceEmbeddingRecord)
        if payload.city_filter:
            query = query.filter(PlaceEmbeddingRecord.city == payload.city_filter)

        all_records = query.all()
        existing_ids = {match.location_id for match in normalized_matches}

        for record in all_records:
            if record.location_id == source_record.location_id or record.location_id in existing_ids:
                continue

            similarity_score = _cosine_similarity(
                source_record.embedding_vector,
                record.embedding_vector,
            )

            normalized_matches.append(
                SimilarPlaceMatch(
                    location_id=record.location_id,
                    name=record.name,
                    city=record.city,
                    country=record.country,
                    category=record.category,
                    similarity_score=similarity_score,
                    why_similar=(
                        f"Similar embedding profile to {source_record.name}"
                        + (f" within {payload.city_filter}." if payload.city_filter else ".")
                    ),
                    relation_type=None,
                    source="embedding",
                    city_match=(record.city == payload.city_filter) if payload.city_filter else False,
                )
            )

        normalized_matches = sorted(
            normalized_matches,
            key=lambda item: item.similarity_score,
            reverse=True,
        )[: payload.top_k]

    return SimilarPlaceResponse(
        source_location_id=payload.source_location_id,
        city_filter_applied=payload.city_filter,
        matches=normalized_matches[: payload.top_k],
    )


def build_destination_guide(payload: DestinationGuideRequest) -> DestinationGuideResponse:
    context = google_places_client.get_destination_context(payload.destination)
    review_bundle = tripadvisor_client.get_destination_reviews(payload.destination)
    review_analysis = analyze_review_bundle(
        location_id=str(review_bundle["location_id"]),
        location_name=str(review_bundle["location_name"]),
        reviews=list(review_bundle["reviews"]),
    )

    interests_text = ", ".join(payload.interests) if payload.interests else "general exploration"
    suggested_areas = list(context["suggested_areas"])
    area_cards = [_build_area_card(area, payload.destination) for area in suggested_areas]
    review_insight = _build_review_insight(
        review_summary=review_analysis.quick_verdict,
        review_signals=review_analysis.themes,
        authenticity=review_analysis.authenticity_label,
    )

    overview = (
        f"{payload.destination} looks like a strong match for a {payload.traveller_type} trip over "
        f"{payload.duration_days} days, especially if you care about {interests_text}. "
        f"The pace here suits a {payload.pace_preference} style with a {payload.budget} budget lens."
    )

    highlights = [
        f"Focus on neighborhoods in {payload.destination} that shape the character of the trip, not just big-name stops.",
        f"Blend headline experiences with interest-led exploration around {interests_text}.",
        "Use live freshness checks before locking specific places or timings.",
    ]

    reasoning = [
        f"This recommendation was shaped around a {payload.traveller_type} travel context.",
        f"{payload.duration_days} days gives enough room for a paced destination overview.",
        "Suggested areas were filtered to prioritize traveler-friendly sub-areas over generic landmarks.",
        f"Review confidence is {review_analysis.authenticity_label}.",
        str(context["freshness_note"]),
    ]

    if payload.traveller_id:
        reasoning.insert(
            1,
            "Traveller-specific persona embedding signals were used to improve downstream destination fit.",
        )

    return DestinationGuideResponse(
        destination=payload.destination,
        traveller_type=payload.traveller_type,
        duration_days=payload.duration_days,
        overview=overview,
        highlights=highlights,
        suggested_areas=suggested_areas,
        area_cards=area_cards,
        reasoning=reasoning,
        review_summary=review_analysis.quick_verdict,
        review_signals=review_analysis.themes,
        review_authenticity=review_analysis.authenticity_label,
        review_insight=review_insight,
        youd_also_love=_build_you_would_also_love(payload),
    )


def compare_destinations(payload: DestinationComparisonRequest) -> DestinationComparisonResponse:
    side_a = _build_comparison_side(
        destination=payload.destination_a,
        traveller_type=payload.traveller_type,
        interests=payload.interests,
        traveller_id=payload.traveller_id,
    )
    side_b = _build_comparison_side(
        destination=payload.destination_b,
        traveller_type=payload.traveller_type,
        interests=payload.interests,
        traveller_id=payload.traveller_id,
    )

    dimensions = _build_comparison_dimensions(
        destination_a=side_a.name,
        destination_b=side_b.name,
        traveller_type=payload.traveller_type,
        interests=payload.interests,
    )

    better_side = side_a if side_a.weighted_score >= side_b.weighted_score else side_b
    comparison_alternatives = _build_you_would_also_love(
        DestinationGuideRequest(
            destination=better_side.name,
            traveller_id=payload.traveller_id,
            duration_days=payload.duration_days,
            traveller_type=payload.traveller_type,
            interests=payload.interests,
            pace_preference=payload.pace_preference,
            budget=payload.budget,
        )
    )

    return DestinationComparisonResponse(
        destination_a=side_a,
        destination_b=side_b,
        dimensions=dimensions,
        verdict=_build_comparison_verdict(
            side_a=side_a,
            side_b=side_b,
            traveller_type=payload.traveller_type,
            interests=payload.interests,
        ),
        planning_recommendation=_build_planning_recommendation(
            side_a=side_a,
            side_b=side_b,
            duration_days=payload.duration_days,
        ),
        next_step_suggestions=[
            f"Plan {payload.duration_days} days in {side_a.name}",
            f"Plan {payload.duration_days} days in {side_b.name}",
            f"Use {side_b.name if side_a.weighted_score >= side_b.weighted_score else side_a.name} as a backup itinerary branch",
        ],
        youd_also_love=comparison_alternatives,
    )


def stream_destination_guide(payload: DestinationGuideRequest) -> Generator[str, None, None]:
    result = build_destination_guide(payload)

    initial_chunk = {
        "type": "meta",
        "destination": result.destination,
        "traveller_type": result.traveller_type,
        "duration_days": result.duration_days,
    }
    yield json.dumps(initial_chunk) + "\n"

    overview_parts = [part.strip() for part in result.overview.split(". ") if part.strip()]
    for part in overview_parts:
        chunk = {
            "type": "content_delta",
            "content": part if part.endswith(".") else f"{part}.",
        }
        yield json.dumps(chunk) + "\n"

    final_chunk = {
        "type": "final",
        "payload": result.model_dump(),
    }
    yield json.dumps(final_chunk) + "\n"