from app.clients.tripadvisor_client import TripadvisorClient


def test_tripadvisor_search_filters_service_and_hotel_results(monkeypatch) -> None:
    client = TripadvisorClient()

    def fake_http_get_json(url: str, *, params: dict, ttl_seconds: int, cache_namespace: str) -> dict:
        return {
            "data": [
                {
                    "location_id": "1",
                    "name": "Kyoto",
                    "address_obj": {"city": "Kyoto", "country": "Japan"},
                    "category": {"name": "Geographic Location"},
                    "rating": 4.7,
                    "num_reviews": 12000,
                },
                {
                    "location_id": "2",
                    "name": "Kyoto Airport Transfer",
                    "address_obj": {"city": "Kyoto", "country": "Japan"},
                    "category": {"name": "Transportation"},
                    "rating": 4.9,
                    "num_reviews": 200,
                },
                {
                    "location_id": "3",
                    "name": "Kyoto Grand Hotel",
                    "address_obj": {"city": "Kyoto", "country": "Japan"},
                    "category": {"name": "Hotel"},
                    "rating": 4.6,
                    "num_reviews": 800,
                },
                {
                    "location_id": "4",
                    "name": "Gion",
                    "address_obj": {"city": "Kyoto", "country": "Japan"},
                    "category": {"name": "Neighborhood"},
                    "rating": 4.8,
                    "num_reviews": 5000,
                },
            ]
        }

    monkeypatch.setattr(client, "_http_get_json", fake_http_get_json)
    client.settings.tripadvisor_api_key = "live_key_for_test"

    results = client.search_locations("Kyoto")

    names = [item.name for item in results]
    assert "Kyoto" in names
    assert "Gion" in names
    assert "Kyoto Airport Transfer" not in names
    assert "Kyoto Grand Hotel" not in names


def test_tripadvisor_reviews_use_direct_location_id_and_cache(monkeypatch) -> None:
    client = TripadvisorClient()
    client.settings.tripadvisor_api_key = "live_key_for_test"

    review_call_count = {"count": 0}

    def fake_live_location_reviews(location_id: str) -> list[dict[str, object]]:
        review_call_count["count"] += 1
        assert location_id == "ta_direct_001"
        return [
            {"rating": 5.0, "text": "Excellent atmosphere and great food."},
            {"rating": 4.0, "text": "Very enjoyable and worth visiting."},
        ]

    def fail_search(*args, **kwargs):
        raise AssertionError("search_locations should not be called when location_id is already supplied.")

    monkeypatch.setattr(client, "_live_location_reviews", fake_live_location_reviews)
    monkeypatch.setattr(client, "search_locations", fail_search)

    first = client.get_destination_reviews(
        "Kyoto",
        location_id="ta_direct_001",
        category="district",
    )
    second = client.get_destination_reviews(
        "Kyoto",
        location_id="ta_direct_001",
        category="district",
    )

    assert first["source"] == "live"
    assert second["source"] == "live"
    assert review_call_count["count"] == 1


def test_tripadvisor_location_photos_are_parsed_and_limited(monkeypatch) -> None:
    client = TripadvisorClient()
    client.settings.tripadvisor_api_key = "live_key_for_test"

    def fake_http_get_json(url: str, *, params: dict, ttl_seconds: int, cache_namespace: str) -> dict:
        return {
            "data": [
                {
                    "id": "photo_1",
                    "caption": "A beautiful heritage street",
                    "images": {
                        "large": {
                            "url": "https://example.com/photo1.jpg",
                            "width": 1200,
                            "height": 800,
                        }
                    },
                },
                {
                    "id": "photo_2",
                    "caption": "Another angle",
                    "images": {
                        "large": {
                            "url": "https://example.com/photo2.jpg",
                            "width": 1000,
                            "height": 750,
                        }
                    },
                },
            ]
        }

    monkeypatch.setattr(client, "_http_get_json", fake_http_get_json)

    photos = client.get_location_photos("ta_kyoto_001", limit=1)

    assert len(photos) == 1
    assert photos[0]["photo_id"] == "photo_1"
    assert photos[0]["source"] == "tripadvisor"
    assert photos[0]["image_url"] == "https://example.com/photo1.jpg"