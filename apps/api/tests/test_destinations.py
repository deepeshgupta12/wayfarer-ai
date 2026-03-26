from app.services import destination_service, review_intelligence_service
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
    assert "filtered" in payload["reasoning"][2].lower()
    assert "review_summary" in payload
    assert isinstance(payload["review_signals"], dict)
    assert "service" in payload["review_signals"]
    assert payload["review_authenticity"] in ["low", "medium", "high"]
    assert "area_cards" in payload
    assert isinstance(payload["area_cards"], list)
    assert len(payload["area_cards"]) >= 1
    assert "review_insight" in payload
    assert isinstance(payload["review_insight"], dict)
    assert "overall_vibe" in payload["review_insight"]


def test_destination_guide_reuses_persisted_review_intelligence(monkeypatch) -> None:
    client = get_test_client()

    def fake_get_destination_reviews(destination: str) -> dict[str, object]:
        return {
            "location_id": "guide_cache_kyoto_001",
            "location_name": "Kyoto",
            "reviews": [
                {"rating": 5, "text": "Friendly staff, delicious food, beautiful atmosphere."},
                {"rating": 4, "text": "Fresh flavors and cozy ambience. Worth the price."},
                {"rating": 5, "text": "Helpful service and tasty dishes."},
            ],
        }

    monkeypatch.setattr(
        destination_service.tripadvisor_client,
        "get_destination_reviews",
        fake_get_destination_reviews,
    )

    first_response = client.post(
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
    assert first_response.status_code == 200

    def _should_not_reanalyze(*args, **kwargs):
        raise AssertionError("Destination guide should reuse persisted review intelligence before re-analysis.")

    monkeypatch.setattr(
        review_intelligence_service,
        "_analyze_review_bundle_live",
        _should_not_reanalyze,
    )

    second_response = client.post(
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
    assert second_response.status_code == 200

    payload = second_response.json()
    assert payload["destination"] == "Kyoto"
    assert "review_summary" in payload
    assert payload["review_authenticity"] in ["low", "medium", "high"]