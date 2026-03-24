import json
import math
from collections.abc import Generator
from typing import Any

from sqlalchemy.orm import Session

from app.clients.google_places_client import GooglePlacesClient
from app.clients.tripadvisor_client import TripadvisorClient
from app.models.place_embedding import PlaceEmbeddingRecord
from app.schemas.destination import (
    DestinationAreaCard,
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
from app.services.review_intelligence_service import analyze_review_bundle

tripadvisor_client = TripadvisorClient()
google_places_client = GooglePlacesClient()


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


def _build_review_insight(review_summary: str, review_signals: dict[str, str], authenticity: str | None) -> DestinationReviewInsight:
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


def search_destinations(payload: DestinationSearchRequest) -> DestinationSearchResponse:
    results = tripadvisor_client.search_locations(
        query=payload.query,
        traveller_type=payload.traveller_type,
        interests=payload.interests,
    )

    return DestinationSearchResponse(
        query=payload.query,
        results=results,
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

    indexed_items: list[DestinationPlaceIndexItem] = []

    for result in results:
        embedding_text = _build_place_embedding_text(
            destination=payload.destination,
            place=result,
            traveller_type=payload.traveller_type,
            interests=payload.interests,
        )
        embedding = get_embedding(embedding_text)

        record = PlaceEmbeddingRecord(
            location_id=result.location_id,
            name=result.name,
            city=result.city,
            country=result.country,
            category=result.category,
            source_destination=payload.destination,
            embedding_provider=embedding.provider,
            embedding_model=embedding.model,
            embedding_dimensions=embedding.dimensions,
            embedding_vector=embedding.vector,
            rating=result.rating,
            review_count=result.review_count,
        )

        db.merge(record)

        indexed_items.append(
            DestinationPlaceIndexItem(
                location_id=result.location_id,
                name=result.name,
                city=result.city,
                country=result.country,
                category=result.category,
                embedding_dimensions=embedding.dimensions,
            )
        )

    db.commit()

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
            matches=[],
        )

    all_records = db.query(PlaceEmbeddingRecord).all()

    scored_matches: list[SimilarPlaceMatch] = []
    for record in all_records:
        if record.location_id == source_record.location_id:
            continue

        similarity_score = _cosine_similarity(
            source_record.embedding_vector,
            record.embedding_vector,
        )

        scored_matches.append(
            SimilarPlaceMatch(
                location_id=record.location_id,
                name=record.name,
                city=record.city,
                country=record.country,
                category=record.category,
                similarity_score=similarity_score,
            )
        )

    scored_matches = sorted(
        scored_matches,
        key=lambda item: item.similarity_score,
        reverse=True,
    )[: payload.top_k]

    return SimilarPlaceResponse(
        source_location_id=payload.source_location_id,
        matches=scored_matches,
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