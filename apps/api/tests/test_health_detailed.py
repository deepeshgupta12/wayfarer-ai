from tests.conftest import get_test_client


def test_health_detailed_endpoint_returns_service_status() -> None:
    client = get_test_client()

    response = client.get("/health/detailed")

    assert response.status_code == 200

    payload = response.json()

    assert "status" in payload
    assert payload["app_name"] == "Wayfarer API"
    assert payload["environment"] == "development"
    assert "services" in payload
    assert "database" in payload["services"]
    assert "redis" in payload["services"]