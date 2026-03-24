from app.clients.google_places_client import GooglePlacesClient
from app.clients.tripadvisor_client import TripadvisorClient


def test_tripadvisor_client_search_returns_results_without_live_keys() -> None:
    client = TripadvisorClient()

    results = client.search_locations(query="Kyoto")

    assert len(results) >= 1
    assert results[0].name == "Kyoto"


def test_google_places_client_context_returns_expected_shape_without_live_keys() -> None:
    client = GooglePlacesClient()

    result = client.get_destination_context("Kyoto")

    assert "suggested_areas" in result
    assert "freshness_note" in result
    assert isinstance(result["suggested_areas"], list)
    assert len(result["suggested_areas"]) >= 1