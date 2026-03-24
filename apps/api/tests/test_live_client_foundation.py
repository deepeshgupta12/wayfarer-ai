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

    assert client._looks_like_area_name("Hotel Granvia Kyoto", "Kyoto") is False
    assert client._looks_like_area_name("Gion District", "Kyoto") is True