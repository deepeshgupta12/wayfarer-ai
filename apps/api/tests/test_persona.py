from tests.conftest import get_test_client


def test_initialize_persona_returns_family_explorer() -> None:
    client = get_test_client()

    response = client.post(
        "/persona/initialize",
        json={
            "travel_style": "midrange",
            "pace_preference": "balanced",
            "group_type": "family",
            "interests": ["culture", "nature"],
        },
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["archetype"] == "family explorer"
    assert "summary" in payload
    assert payload["signals"]["group_type"] == "family"


def test_initialize_persona_returns_budget_backpacker() -> None:
    client = get_test_client()

    response = client.post(
        "/persona/initialize",
        json={
            "travel_style": "budget",
            "pace_preference": "balanced",
            "group_type": "solo",
            "interests": ["adventure", "nature"],
        },
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["archetype"] == "budget backpacker"
    assert payload["signals"]["travel_style"] == "budget"


def test_refresh_persona_from_memory_updates_signals() -> None:
    client = get_test_client()
    traveller_id = "traveller_persona_refresh_001"

    initialize_response = client.post(
        "/persona/initialize-and-save",
        json={
            "traveller_id": traveller_id,
            "travel_style": "midrange",
            "pace_preference": "balanced",
            "group_type": "solo",
            "interests": ["culture", "nature"],
        },
    )
    assert initialize_response.status_code == 200

    client.post(
        "/traveller-memory",
        json={
            "traveller_id": traveller_id,
            "event_type": "destination_guide_requested",
            "source_surface": "assistant",
            "payload": {
                "query": "Best foodie neighborhoods in Lisbon for a couple",
                "destination": "Lisbon",
                "duration_days": 4,
                "traveller_type": "couple",
                "interests": ["food", "culture", "nightlife"],
                "budget": "midrange",
            },
        },
    )

    client.post(
        "/traveller-memory",
        json={
            "traveller_id": traveller_id,
            "event_type": "destination_guide_generated",
            "source_surface": "assistant",
            "payload": {
                "query": "Best foodie neighborhoods in Lisbon for a couple",
                "destination": "Lisbon",
                "duration_days": 4,
                "traveller_type": "couple",
                "interests": ["food", "culture", "nightlife"],
                "budget": "midrange",
            },
        },
    )

    refresh_response = client.post(f"/persona/refresh-from-memory/{traveller_id}")
    assert refresh_response.status_code == 200

    payload = refresh_response.json()

    assert payload["traveller_id"] == traveller_id
    assert payload["signals"]["group_type"] == "couple"
    assert "food" in payload["signals"]["interests"]
    assert payload["signals"]["updated_from_memory"] is True
    assert payload["signals"]["memory_events_used"] >= 2
    assert payload["signals"]["bayesian_update_v1"] is True
    assert "posterior" in payload["signals"]
    assert "group_type" in payload["signals"]["posterior"]
    assert payload["signals"]["posterior"]["group_type"]["couple"] > payload["signals"]["posterior"]["group_type"]["solo"]