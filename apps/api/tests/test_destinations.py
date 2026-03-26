from app.services import destination_service, review_intelligence_service
from tests.conftest import get_test_client
from types import SimpleNamespace


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

def test_destination_search_applies_persona_relevance_reranking(monkeypatch) -> None:
    client = get_test_client()

    search_results = [
        SimpleNamespace(
            location_id="dest_rank_001",
            name="Kyoto Fast Core",
            city="Kyoto",
            country="Japan",
            category="city",
            rating=4.9,
            review_count=12000,
        ),
        SimpleNamespace(
            location_id="dest_rank_002",
            name="Kyoto Slow Lanes",
            city="Kyoto",
            country="Japan",
            category="neighborhood",
            rating=4.4,
            review_count=7000,
        ),
    ]

    monkeypatch.setattr(
        destination_service.tripadvisor_client,
        "search_locations",
        lambda query, traveller_type, interests: search_results,
    )

    def fake_persona_relevance(db, traveller_id, text: str) -> float | None:
        if "Kyoto Slow Lanes" in text:
            return 0.96
        if "Kyoto Fast Core" in text:
            return 0.10
        return 0.0

    monkeypatch.setattr(
        destination_service,
        "calculate_persona_relevance_score",
        fake_persona_relevance,
    )

    response = client.post(
        "/destinations/search",
        json={
            "query": "Kyoto",
            "traveller_id": "traveller_rank_001",
            "traveller_type": "solo",
            "interests": ["culture", "wellness"],
        },
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["results"][0]["name"] == "Kyoto Slow Lanes"
    assert payload["results"][1]["name"] == "Kyoto Fast Core"

def test_destination_compare_applies_persona_weighting(monkeypatch) -> None:
    client = get_test_client()

    def fake_search_locations(query: str, traveller_type: str | None, interests: list[str]):
        if query.lower() == "kyoto":
            return [
                SimpleNamespace(
                    location_id="cmp_kyoto_001",
                    name="Kyoto",
                    city="Kyoto",
                    country="Japan",
                    category="city",
                    rating=4.8,
                    review_count=12000,
                )
            ]
        return [
            SimpleNamespace(
                location_id="cmp_tokyo_001",
                name="Tokyo",
                city="Tokyo",
                country="Japan",
                category="city",
                rating=4.8,
                review_count=14000,
            )
        ]

    monkeypatch.setattr(
        destination_service.tripadvisor_client,
        "search_locations",
        fake_search_locations,
    )

    monkeypatch.setattr(
        destination_service.tripadvisor_client,
        "get_destination_reviews",
        lambda destination: {
            "location_id": f"reviews_{destination.lower()}",
            "location_name": destination,
            "reviews": [
                {"rating": 5, "text": "Great food and atmosphere."},
                {"rating": 4, "text": "Walkable and enjoyable."},
            ],
        },
    )

    monkeypatch.setattr(
        destination_service.google_places_client,
        "get_destination_context",
        lambda destination: {
            "suggested_areas": ["Central Area"],
            "freshness_note": "Fresh enough",
        },
    )

    def fake_persona_relevance(db, traveller_id, text: str) -> float | None:
        if "Tokyo" in text:
            return 0.98
        if "Kyoto" in text:
            return 0.05
        return 0.0

    monkeypatch.setattr(
        destination_service,
        "calculate_persona_relevance_score",
        fake_persona_relevance,
    )

    response = client.post(
        "/destinations/compare",
        json={
            "destination_a": "Kyoto",
            "destination_b": "Tokyo",
            "traveller_id": "traveller_compare_001",
            "traveller_type": "solo",
            "interests": ["food", "nightlife"],
            "duration_days": 3,
        },
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["destination_b"]["name"] == "Tokyo"
    assert payload["destination_b"]["weighted_score"] > payload["destination_a"]["weighted_score"]
    assert "Tokyo comes out ahead" in payload["verdict"]