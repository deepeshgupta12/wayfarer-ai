from tests.conftest import get_test_client


def _create_enriched_trip_with_saved_trip(client, traveller_id: str, brief: str) -> dict:
    create_plan_response = client.post(
        "/trip-plans/parse-and-save",
        json={
            "traveller_id": traveller_id,
            "brief": brief,
            "source_surface": "assistant",
        },
    )
    assert create_plan_response.status_code == 200
    planning_session_id = create_plan_response.json()["planning_session_id"]

    enrich_response = client.post(f"/trip-plans/{planning_session_id}/enrich")
    assert enrich_response.status_code == 200

    promote_response = client.post(
        f"/trips/from-plan/{planning_session_id}",
        json={
            "title": "Photo intelligence trip",
            "companions": "solo",
            "status": "planning",
            "source_surface": "assistant",
        },
    )
    assert promote_response.status_code == 200

    return {
        "planning_session_id": planning_session_id,
        "trip_id": promote_response.json()["trip_id"],
    }


def test_destination_search_returns_ranked_photos() -> None:
    client = get_test_client()

    response = client.post(
        "/destinations/search",
        json={
            "query": "Kyoto",
            "traveller_type": "solo",
            "interests": ["food", "culture"],
        },
    )
    assert response.status_code == 200
    payload = response.json()

    assert payload["results"]
    assert "photos" in payload["results"][0]
    assert isinstance(payload["results"][0]["photos"], list)
    assert len(payload["results"][0]["photos"]) >= 1
    assert "visual_score" in payload["results"][0]["photos"][0]


def test_nearby_results_return_ranked_photos() -> None:
    client = get_test_client()

    response = client.post(
        "/destinations/nearby",
        json={
            "latitude": 35.0116,
            "longitude": 135.7681,
            "city": "Kyoto",
            "country": "Japan",
            "query": "food nearby right now",
            "traveller_type": "solo",
            "interests": ["food", "culture"],
            "budget": "midrange",
            "limit": 3,
            "starting_radius_meters": 800,
            "max_radius_meters": 3000,
            "adaptive_radius": True,
            "context": {
                "intent_hint": "food",
                "transport_mode": "walk",
                "available_minutes": 75,
                "current_slot_type": "lunch",
                "current_city": "Kyoto",
                "current_country": "Japan",
            },
        },
    )
    assert response.status_code == 200
    payload = response.json()

    assert payload["recommendations"]
    assert "photos" in payload["recommendations"][0]
    assert len(payload["recommendations"][0]["photos"]) >= 1


def test_trip_plan_enrich_returns_candidate_and_slot_photos() -> None:
    client = get_test_client()

    create_response = client.post(
        "/trip-plans/parse-and-save",
        json={
            "traveller_id": "traveller_photo_trip_001",
            "brief": "I have 4 days in Tokyo for a solo trip, mid-budget, balanced pace, love food and culture",
            "source_surface": "assistant",
        },
    )
    assert create_response.status_code == 200
    planning_session_id = create_response.json()["planning_session_id"]

    enrich_response = client.post(f"/trip-plans/{planning_session_id}/enrich")
    assert enrich_response.status_code == 200
    payload = enrich_response.json()

    assert payload["candidate_places"]
    assert "photos" in payload["candidate_places"][0]
    assert len(payload["candidate_places"][0]["photos"]) >= 1

    assert payload["itinerary_skeleton"]
    first_day = payload["itinerary_skeleton"][0]
    assert first_day["slots"]
    assert "assigned_place_photos" in first_day["slots"][0]