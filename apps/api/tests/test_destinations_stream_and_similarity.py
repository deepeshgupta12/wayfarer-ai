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
    assert isinstance(payload["matches"], list)


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