from tests.conftest import get_test_client


def test_review_intelligence_analyze_returns_expected_structure() -> None:
    client = get_test_client()

    response = client.post(
        "/review-intelligence/analyze",
        json={
            "location_id": "loc_kyoto_001",
            "location_name": "Kyoto Garden Bistro",
            "reviews": [
                {"rating": 5, "text": "Friendly staff, delicious food, beautiful atmosphere."},
                {"rating": 4, "text": "Fresh flavors and cozy ambience. Worth the price."},
                {"rating": 5, "text": "Helpful service and tasty dishes."},
            ],
        },
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["location_id"] == "loc_kyoto_001"
    assert payload["location_name"] == "Kyoto Garden Bistro"
    assert "quick_verdict" in payload
    assert payload["review_count"] == 3
    assert "themes" in payload
    assert "service" in payload["themes"]
    assert "food_quality" in payload["themes"]
    assert "value" in payload["themes"]
    assert "ambience" in payload["themes"]


def test_review_intelligence_analyze_and_save_returns_saved_payload() -> None:
    client = get_test_client()

    response = client.post(
        "/review-intelligence/analyze-and-save",
        json={
            "location_id": "loc_lisbon_002",
            "location_name": "Lisbon Sunset Cafe",
            "reviews": [
                {"rating": 4, "text": "Helpful staff and tasty brunch."},
                {"rating": 5, "text": "Beautiful atmosphere and great value."},
            ],
        },
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["location_id"] == "loc_lisbon_002"
    assert payload["saved"] is True
    assert payload["review_count"] == 2


def test_review_intelligence_marks_negative_food_signal_as_caution() -> None:
    client = get_test_client()

    response = client.post(
        "/review-intelligence/analyze",
        json={
            "location_id": "loc_test_003",
            "location_name": "Mixed Signal Diner",
            "reviews": [
                {"rating": 2, "text": "Friendly staff but bland food and poor value."},
                {"rating": 3, "text": "Helpful service, but the food was cold and overpriced."},
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["themes"]["service"] in ["positive", "neutral"]
    assert payload["themes"]["food_quality"] == "caution"
    assert payload["themes"]["value"] == "caution"