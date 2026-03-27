from tests.conftest import get_test_client


def test_destination_hidden_gems_api_returns_ranked_results() -> None:
    client = get_test_client()

    response = client.post(
        "/destinations/gems",
        json={
            "destination": "Kyoto",
            "traveller_type": "solo",
            "interests": ["food", "culture"],
            "pace_preference": "relaxed",
            "budget": "midrange",
            "limit": 3,
        },
    )
    assert response.status_code == 200
    payload = response.json()

    assert payload["destination"] == "Kyoto"
    assert payload["total"] >= 1
    assert len(payload["gems"]) >= 1
    assert "gem_score" in payload["gems"][0]
    assert "why_hidden_gem" in payload["gems"][0]
    assert "fit_reasons" in payload["gems"][0]


def test_destination_guide_includes_hidden_gems() -> None:
    client = get_test_client()

    response = client.post(
        "/destinations/guide",
        json={
            "destination": "Lisbon",
            "traveller_type": "solo",
            "duration_days": 4,
            "interests": ["food", "culture"],
            "pace_preference": "relaxed",
            "budget": "midrange",
        },
    )
    assert response.status_code == 200
    payload = response.json()

    assert "hidden_gems" in payload
    assert isinstance(payload["hidden_gems"], list)
    assert len(payload["hidden_gems"]) >= 1
    assert "why_hidden_gem" in payload["hidden_gems"][0]