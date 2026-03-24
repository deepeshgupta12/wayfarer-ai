from app.clients.google_places_client import GooglePlacesClient
from app.clients.tripadvisor_client import TripadvisorClient


def test_tripadvisor_client_search_returns_results_without_live_keys() -> None:
    client = TripadvisorClient()

    results = client.search_locations(query="Kyoto")

    assert len(results) >= 1
    assert "Kyoto" in results[0].name


def test_google_places_client_context_returns_expected_shape_without_live_keys() -> None:
    client = GooglePlacesClient()

    result = client.get_destination_context("Kyoto")

    assert "suggested_areas" in result
    assert "freshness_note" in result
    assert isinstance(result["suggested_areas"], list)
    assert len(result["suggested_areas"]) >= 1


def test_google_places_area_filter_rejects_hotel_like_names() -> None:
    client = GooglePlacesClient()

    assert client._is_blocked_area_name("Hotel Granvia Kyoto") is True
    assert client._score_area_name("Gion District", "Kyoto") > 0


def test_google_places_area_filter_rejects_market_like_names() -> None:
    client = GooglePlacesClient()

    assert client._is_blocked_area_name("Nishiki Market") is True
    assert client._score_area_name("Higashiyama District", "Kyoto") > 0


def test_google_places_area_filter_rejects_intersection_like_names() -> None:
    client = GooglePlacesClient()

    assert client._is_blocked_area_name("Kyoto Downtown Intersection (Shijo-Kawaramachi)") is True


def test_google_places_area_canonicalizes_known_destination_subareas() -> None:
    client = GooglePlacesClient()

    assert client._canonicalize_area_candidate("Gion District", "Kyoto") == "Gion"
    assert client._canonicalize_area_candidate("Higashiyama District", "Kyoto") == "Higashiyama"


def test_google_places_area_filter_rejects_country_like_names() -> None:
    client = GooglePlacesClient()

    assert client._is_country_like_name("Japan") is True
    assert client._score_area_name("Japan", "Kyoto") < 0


def test_google_places_quality_guardrails_can_force_fallback() -> None:
    client = GooglePlacesClient()

    payload = {
        "places": [
            {"displayName": {"text": "Japan"}, "formattedAddress": "Japan"},
            {"displayName": {"text": "Arashiyama Bamboo Forest"}, "formattedAddress": "Kyoto, Japan"},
            {"displayName": {"text": "The Ritz-Carlton, Kyoto"}, "formattedAddress": "Kyoto, Japan"},
        ]
    }

    assert client._extract_suggested_areas(payload, "Kyoto") == []