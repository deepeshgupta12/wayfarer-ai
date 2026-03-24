from tests.conftest import get_test_client


def test_initialize_and_save_persona_returns_persisted_payload() -> None:
    client = get_test_client()

    response = client.post(
        "/persona/initialize-and-save",
        json={
            "traveller_id": "traveller_test_001",
            "travel_style": "budget",
            "pace_preference": "balanced",
            "group_type": "solo",
            "interests": ["adventure", "nature"],
        },
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["traveller_id"] == "traveller_test_001"
    assert payload["archetype"] == "budget backpacker"
    assert payload["signals"]["travel_style"] == "budget"