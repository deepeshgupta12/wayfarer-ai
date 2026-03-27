from uuid import uuid4

from tests.conftest import get_test_client


def test_create_traveller_memory_event() -> None:
    client = get_test_client()
    traveller_id = f"traveller_memory_test_001_{uuid4().hex}"

    response = client.post(
        "/traveller-memory",
        json={
            "traveller_id": traveller_id,
            "event_type": "destination_guide_requested",
            "source_surface": "assistant",
            "payload": {
                "query": "3 days in Kyoto for food and culture",
                "destination": "Kyoto",
            },
        },
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["saved"] is True
    assert payload["traveller_id"] == traveller_id
    assert payload["event_type"] == "destination_guide_requested"
    assert payload["source_surface"] == "assistant"
    assert payload["payload"]["destination"] == "Kyoto"
    assert "id" in payload
    assert "created_at" in payload


def test_list_traveller_memory_events() -> None:
    client = get_test_client()
    traveller_id = f"traveller_memory_test_002_{uuid4().hex}"

    client.post(
        "/traveller-memory",
        json={
            "traveller_id": traveller_id,
            "event_type": "destination_guide_requested",
            "source_surface": "assistant",
            "payload": {"destination": "Lisbon"},
        },
    )

    client.post(
        "/traveller-memory",
        json={
            "traveller_id": traveller_id,
            "event_type": "destination_guide_generated",
            "source_surface": "assistant",
            "payload": {"destination": "Lisbon", "review_authenticity": "medium"},
        },
    )

    response = client.get(f"/traveller-memory/{traveller_id}?limit=10")

    assert response.status_code == 200

    payload = response.json()

    assert payload["traveller_id"] == traveller_id
    assert payload["total"] >= 2
    assert isinstance(payload["items"], list)
    assert len(payload["items"]) >= 2
    assert payload["items"][0]["traveller_id"] == traveller_id


def test_list_traveller_memory_supports_event_type_and_planning_session_filters() -> None:
    client = get_test_client()
    traveller_id = f"traveller_memory_test_003_{uuid4().hex}"

    client.post(
        "/traveller-memory",
        json={
            "traveller_id": traveller_id,
            "event_type": "selected_place_saved",
            "source_surface": "itinerary",
            "payload": {
                "planning_session_id": "plan_alpha",
                "location_id": "ta_kyoto_gion_001",
            },
        },
    )

    client.post(
        "/traveller-memory",
        json={
            "traveller_id": traveller_id,
            "event_type": "skipped_recommendation",
            "source_surface": "assistant",
            "payload": {
                "planning_session_id": "plan_alpha",
                "location_id": "ta_kyoto_pontocho_001",
            },
        },
    )

    client.post(
        "/traveller-memory",
        json={
            "traveller_id": traveller_id,
            "event_type": "itinerary_version_snapshot",
            "source_surface": "planner_modal",
            "payload": {
                "planning_session_id": "plan_beta",
                "version_number": 2,
            },
        },
    )

    filtered_response = client.get(
        f"/traveller-memory/{traveller_id}?limit=10&event_type=selected_place_saved&planning_session_id=plan_alpha"
    )
    assert filtered_response.status_code == 200

    payload = filtered_response.json()
    assert payload["total"] == 1
    assert len(payload["items"]) == 1
    assert payload["items"][0]["event_type"] == "selected_place_saved"
    assert payload["items"][0]["payload"]["planning_session_id"] == "plan_alpha"

def test_list_traveller_memory_includes_live_gem_events() -> None:
    client = get_test_client()
    traveller_id = f"traveller_memory_gem_{uuid4().hex}"

    create_response = client.post(
        "/traveller-memory",
        json={
            "traveller_id": traveller_id,
            "event_type": "live_gem_saved",
            "source_surface": "live_runtime",
            "payload": {
                "trip_id": "trip_demo",
                "planning_session_id": "plan_demo",
                "location_id": "ta_lisbon_alfama_001",
                "gem_score": 82.6,
            },
        },
    )
    assert create_response.status_code == 200

    response = client.get(
        f"/traveller-memory/{traveller_id}",
        params={"limit": 10, "event_type": "live_gem_saved"},
    )
    assert response.status_code == 200

    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["event_type"] == "live_gem_saved"
    assert payload["items"][0]["payload"]["location_id"] == "ta_lisbon_alfama_001"