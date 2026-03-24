from tests.conftest import get_test_client


def test_destination_search_returns_results() -> None:
    client = get_test_client()

    response = client.post(
        "/destinations/search",
        json={
            "query": "Kyoto",
            "traveller_type": "couple",
            "interests": ["food", "culture"],
        },
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["query"] == "Kyoto"
    assert isinstance(payload["results"], list)
    assert len(payload["results"]) >= 1
    assert "Kyoto" in payload["results"][0]["name"]


def test_destination_guide_returns_expected_structure() -> None:
    client = get_test_client()

    response = client.post(
        "/destinations/guide",
        json={
            "destination": "Kyoto",
            "duration_days": 3,
            "traveller_type": "couple",
            "interests": ["food", "culture"],
            "pace_preference": "balanced",
            "budget": "midrange",
        },
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["destination"] == "Kyoto"
    assert payload["traveller_type"] == "couple"
    assert payload["duration_days"] == 3
    assert isinstance(payload["highlights"], list)
    assert len(payload["highlights"]) >= 1
    assert isinstance(payload["suggested_areas"], list)
    assert len(payload["suggested_areas"]) >= 1
    assert "neighborhood" in payload["reasoning"][2].lower()