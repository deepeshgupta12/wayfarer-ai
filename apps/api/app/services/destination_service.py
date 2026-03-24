from app.clients.google_places_client import GooglePlacesClient
from app.clients.tripadvisor_client import TripadvisorClient
from app.schemas.destination import (
    DestinationGuideRequest,
    DestinationGuideResponse,
    DestinationSearchRequest,
    DestinationSearchResponse,
)

tripadvisor_client = TripadvisorClient()
google_places_client = GooglePlacesClient()


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


def build_destination_guide(payload: DestinationGuideRequest) -> DestinationGuideResponse:
    context = google_places_client.get_destination_context(payload.destination)
    interests_text = ", ".join(payload.interests) if payload.interests else "general exploration"
    suggested_areas = list(context["suggested_areas"])

    overview = (
        f"{payload.destination} is a strong fit for a {payload.traveller_type} traveller over "
        f"{payload.duration_days} days, especially if you enjoy {interests_text}. "
        f"This guide is paced for a {payload.pace_preference} rhythm with a {payload.budget} budget lens."
    )

    highlights = [
        f"Prioritize destination-defining neighborhoods in {payload.destination}, not generic place listings.",
        f"Blend landmark experiences with interest-led discovery around {interests_text}.",
        "Use review intelligence and freshness checks before finalizing live itineraries.",
    ]

    reasoning = [
        f"The destination was framed for traveller_type={payload.traveller_type}.",
        f"The duration of {payload.duration_days} days supports a paced overview rather than rushed coverage.",
        f"Suggested areas were normalized and ranked to prefer sub-areas over landmarks in {payload.destination}.",
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
    )