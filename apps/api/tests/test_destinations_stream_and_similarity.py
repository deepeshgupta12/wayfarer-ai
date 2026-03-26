from tests.conftest import get_test_client


def test_destination_place_index_returns_items() -> None:
    client = get_test_client()

    response = client.post(
        "/destinations/places/index",
        json={
            "destination": "Kyoto",
            "traveller_type": "couple",
            "interests": ["food", "culture"],
        },
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["destination"] == "Kyoto"
    assert payload["indexed_count"] >= 1
    assert isinstance(payload["items"], list)
    assert len(payload["items"]) >= 1
    assert "location_id" in payload["items"][0]


def test_destination_place_similarity_returns_matches() -> None:
    client = get_test_client()

    index_response = client.post(
        "/destinations/places/index",
        json={
            "destination": "Kyoto",
            "traveller_type": "couple",
            "interests": ["food", "culture"],
        },
    )
    assert index_response.status_code == 200

    indexed_items = index_response.json()["items"]
    source_location_id = indexed_items[0]["location_id"]

    response = client.post(
        "/destinations/places/similar",
        json={
            "source_location_id": source_location_id,
            "top_k": 3,
        },
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["source_location_id"] == source_location_id
    assert payload["city_filter_applied"] is None
    assert isinstance(payload["matches"], list)


def test_destination_place_similarity_supports_city_filter() -> None:
    client = get_test_client()

    kyoto_index = client.post(
        "/destinations/places/index",
        json={
            "destination": "Kyoto",
            "traveller_type": "solo",
            "interests": ["food", "culture"],
        },
    )
    assert kyoto_index.status_code == 200

    tokyo_index = client.post(
        "/destinations/places/index",
        json={
            "destination": "Tokyo",
            "traveller_type": "solo",
            "interests": ["food", "culture"],
        },
    )
    assert tokyo_index.status_code == 200

    source_location_id = kyoto_index.json()["items"][0]["location_id"]

    response = client.post(
        "/destinations/places/similar",
        json={
            "source_location_id": source_location_id,
            "top_k": 5,
            "city_filter": "Kyoto",
        },
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["city_filter_applied"] == "Kyoto"
    assert isinstance(payload["matches"], list)

    for match in payload["matches"]:
        assert match["city"] == "Kyoto"
        assert match["city_match"] is True


def test_destination_guide_returns_youd_also_love_recommendations() -> None:
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

    assert "youd_also_love" in payload
    assert isinstance(payload["youd_also_love"], list)
    assert len(payload["youd_also_love"]) >= 1
    assert payload["youd_also_love"][0]["name"] != "Kyoto"


def test_destination_compare_returns_structured_persona_weighted_output() -> None:
    client = get_test_client()

    response = client.post(
        "/destinations/compare",
        json={
            "destination_a": "Prague",
            "destination_b": "Budapest",
            "traveller_type": "couple",
            "interests": ["culture", "food"],
            "pace_preference": "balanced",
            "budget": "midrange",
            "duration_days": 4,
        },
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["destination_a"]["name"] == "Prague"
    assert payload["destination_b"]["name"] == "Budapest"
    assert isinstance(payload["dimensions"], list)
    assert len(payload["dimensions"]) == 10
    assert "verdict" in payload
    assert "planning_recommendation" in payload
    assert isinstance(payload["next_step_suggestions"], list)
    assert payload["dimensions"][0]["weight"] > 0


def test_destination_guide_stream_returns_ndjson_chunks() -> None:
    client = get_test_client()

    response = client.post(
        "/destinations/guide/stream",
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
    body = response.text

    assert '"type": "meta"' in body
    assert '"type": "content_delta"' in body
    assert '"type": "final"' in body
    assert '"review_summary"' in body
    assert '"youd_also_love"' in body