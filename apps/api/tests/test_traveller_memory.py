from tests.conftest import get_test_client


def test_create_traveller_memory_event() -> None:
    client = get_test_client()

    response = client.post(
        "/traveller-memory",
        json={
            "traveller_id": "traveller_memory_test_001",
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
    assert payload["traveller_id"] == "traveller_memory_test_001"
    assert payload["event_type"] == "destination_guide_requested"
    assert payload["source_surface"] == "assistant"
    assert payload["payload"]["destination"] == "Kyoto"
    assert "id" in payload
    assert "created_at" in payload


def test_list_traveller_memory_events() -> None:
    client = get_test_client()
    traveller_id = "traveller_memory_test_002"

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