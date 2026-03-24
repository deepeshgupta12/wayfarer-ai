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