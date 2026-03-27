from tests.conftest import get_test_client


def test_destinations_nearby_api_returns_adaptive_ranked_results() -> None:
    client = get_test_client()

    response = client.post(
        "/destinations/nearby",
        json={
            "latitude": 35.0116,
            "longitude": 135.7681,
            "city": "Kyoto",
            "country": "Japan",
            "query": "food nearby right now",
            "traveller_type": "solo",
            "interests": ["food", "culture"],
            "budget": "midrange",
            "limit": 3,
            "starting_radius_meters": 800,
            "max_radius_meters": 3000,
            "adaptive_radius": True,
            "context": {
                "intent_hint": "food",
                "transport_mode": "walk",
                "available_minutes": 75,
                "current_slot_type": "lunch",
                "current_city": "Kyoto",
                "current_country": "Japan",
            },
        },
    )
    assert response.status_code == 200
    payload = response.json()

    assert payload["city"] == "Kyoto"
    assert payload["total"] >= 1
    assert len(payload["recommendations"]) >= 1
    assert payload["radius_used_meters"] >= 800
    assert len(payload["search_expansions"]) >= 1
    assert "live_score" in payload["recommendations"][0]
    assert "distance_meters" in payload["recommendations"][0]
    assert "why_recommended" in payload["recommendations"][0]


def test_destinations_nearby_api_respects_blocked_location_ids() -> None:
    client = get_test_client()

    response = client.post(
        "/destinations/nearby",
        json={
            "latitude": 38.7107,
            "longitude": -9.1435,
            "city": "Lisbon",
            "country": "Portugal",
            "query": "something nearby",
            "traveller_type": "solo",
            "interests": ["food", "culture"],
            "budget": "midrange",
            "limit": 5,
            "starting_radius_meters": 800,
            "max_radius_meters": 3000,
            "adaptive_radius": True,
            "context": {
                "intent_hint": "culture",
                "transport_mode": "walk",
                "available_minutes": 90,
                "current_slot_type": "afternoon",
                "current_city": "Lisbon",
                "current_country": "Portugal",
                "exclude_location_ids": ["ta_lisbon_chiado_001"],
                "closed_location_ids": ["ta_lisbon_bairro_alto_001"],
            },
        },
    )
    assert response.status_code == 200
    payload = response.json()

    returned_ids = {item["location_id"] for item in payload["recommendations"]}
    assert "ta_lisbon_chiado_001" not in returned_ids
    assert "ta_lisbon_bairro_alto_001" not in returned_ids
    assert "ta_lisbon_chiado_001" in payload["blocked_location_ids"]
    assert "ta_lisbon_bairro_alto_001" in payload["blocked_location_ids"]