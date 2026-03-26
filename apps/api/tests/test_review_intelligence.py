from app.db.session import get_db_session
from app.schemas.review_intelligence import ReviewIntelligenceRequest
from app.services import review_intelligence_service
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
    assert payload["cache_status"] in ["persisted", "reused", "refreshed"]


def test_review_intelligence_get_saved_record_returns_persisted_payload() -> None:
    client = get_test_client()
    location_id = "loc_lisbon_get_001"

    save_response = client.post(
        "/review-intelligence/analyze-and-save",
        json={
            "location_id": location_id,
            "location_name": "Lisbon Saved Cafe",
            "reviews": [
                {"rating": 4, "text": "Helpful staff and tasty brunch."},
                {"rating": 5, "text": "Beautiful atmosphere and great value."},
            ],
        },
    )
    assert save_response.status_code == 200

    get_response = client.get(f"/review-intelligence/{location_id}")
    assert get_response.status_code == 200

    payload = get_response.json()
    assert payload["location_id"] == location_id
    assert payload["saved"] is True
    assert payload["cache_status"] == "persisted"


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


def test_review_intelligence_returns_valid_labels_only() -> None:
    client = get_test_client()

    response = client.post(
        "/review-intelligence/analyze",
        json={
            "location_id": "loc_test_004",
            "location_name": "Signal Check Cafe",
            "reviews": [
                {"rating": 4, "text": "Friendly staff and beautiful atmosphere."},
                {"rating": 4, "text": "Good value and tasty food."},
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["themes"]["service"] in ["positive", "neutral", "caution"]
    assert payload["themes"]["food_quality"] in ["positive", "neutral", "caution"]
    assert payload["themes"]["value"] in ["positive", "neutral", "caution"]
    assert payload["themes"]["ambience"] in ["positive", "neutral", "caution"]


def test_review_intelligence_uses_llm_output_when_valid(monkeypatch) -> None:
    client = get_test_client()

    monkeypatch.setattr(
        review_intelligence_service,
        "_extract_themes_with_llm",
        lambda location_name, reviews: {
            "service": "positive",
            "food_quality": "neutral",
            "value": "caution",
            "ambience": "positive",
        },
    )

    response = client.post(
        "/review-intelligence/analyze",
        json={
            "location_id": "loc_test_005",
            "location_name": "LLM Guided Bistro",
            "reviews": [
                {"rating": 4, "text": "Some mixed signals but overall decent."},
                {"rating": 4, "text": "Atmosphere was lovely."},
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["themes"] == {
        "service": "positive",
        "food_quality": "neutral",
        "value": "caution",
        "ambience": "positive",
    }


def test_review_intelligence_falls_back_when_llm_output_is_invalid(monkeypatch) -> None:
    client = get_test_client()

    monkeypatch.setattr(
        review_intelligence_service,
        "_extract_themes_with_llm",
        lambda location_name, reviews: None,
    )

    response = client.post(
        "/review-intelligence/analyze",
        json={
            "location_id": "loc_test_006",
            "location_name": "Fallback Bistro",
            "reviews": [
                {"rating": 5, "text": "Friendly staff, delicious food, beautiful atmosphere."},
                {"rating": 4, "text": "Helpful service and good value."},
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["themes"]["service"] in ["positive", "neutral", "caution"]
    assert payload["themes"]["food_quality"] in ["positive", "neutral", "caution"]
    assert payload["themes"]["value"] in ["positive", "neutral", "caution"]
    assert payload["themes"]["ambience"] in ["positive", "neutral", "caution"]


def test_review_intelligence_reuses_cached_analysis_when_reviews_are_unchanged(monkeypatch) -> None:
    db = get_db_session()
    try:
        payload = ReviewIntelligenceRequest(
            location_id="loc_cache_test_001",
            location_name="Cache Test Cafe",
            reviews=[
                {"rating": 5, "text": "Friendly staff and tasty food."},
                {"rating": 4, "text": "Great value and lovely ambience."},
            ],
        )

        first_result = review_intelligence_service.analyze_and_persist_reviews(db, payload)
        assert first_result.saved is True
        assert first_result.cache_status == "persisted"

        def _should_not_reanalyze(*args, **kwargs):
            raise AssertionError("Live re-analysis should not run when cached review intelligence is reusable.")

        monkeypatch.setattr(
            review_intelligence_service,
            "_analyze_review_bundle_live",
            _should_not_reanalyze,
        )

        second_result = review_intelligence_service.get_or_refresh_review_intelligence(
            db=db,
            location_id=payload.location_id,
            location_name=payload.location_name,
            reviews=[{"rating": review.rating, "text": review.text} for review in payload.reviews],
        )

        assert second_result.saved is True
        assert second_result.cache_status == "reused"
        assert second_result.location_id == payload.location_id
    finally:
        db.close()