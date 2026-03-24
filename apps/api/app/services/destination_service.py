import json
import math
from collections.abc import Generator
from typing import Any

from sqlalchemy.orm import Session

from app.clients.google_places_client import GooglePlacesClient
from app.clients.tripadvisor_client import TripadvisorClient
from app.models.place_embedding import PlaceEmbeddingRecord
from app.schemas.destination import (
    DestinationGuideRequest,
    DestinationGuideResponse,
    DestinationPlaceIndexItem,
    DestinationPlaceIndexRequest,
    DestinationPlaceIndexResponse,
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

    overview = (
        f"{payload.destination} is a strong fit for a {payload.traveller_type} traveller over "
        f"{payload.duration_days} days, especially if you enjoy {interests_text}. "
        f"This guide is paced for a {payload.pace_preference} rhythm with a {payload.budget} budget lens. "
        f"Review-backed signals indicate {review_analysis.quick_verdict.lower()}"
    )

    highlights = [
        f"Review-backed signal: {review_analysis.quick_verdict}",
        f"Prioritize destination-defining neighborhoods in {payload.destination}, not generic place listings.",
        f"Blend landmark experiences with interest-led discovery around {interests_text}.",
    ]

    reasoning = [
        f"The destination was framed for traveller_type={payload.traveller_type}.",
        f"The duration of {payload.duration_days} days supports a paced overview rather than rushed coverage.",
        f"Suggested areas were canonicalized, quality-filtered, and guarded against POI leakage in {payload.destination}.",
        f"Review intelligence source={review_bundle['source']} with authenticity={review_analysis.authenticity_label}.",
        str(context["freshness_note"]),
    ]

    return DestinationGuideResponse(
        destination=payload.destination,
        traveller_type=payload.traveller_type,
        duration_days=payload.duration_days,
        overview=overview,
        highlights=highlights,
        suggested_areas=suggested_areas,
        reasoning=reasoning,
        review_summary=review_analysis.quick_verdict,
        review_signals=review_analysis.themes,
        review_authenticity=review_analysis.authenticity_label,
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