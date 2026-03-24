from tests.conftest import get_test_client


def test_root_endpoint_returns_expected_payload() -> None:
    client = get_test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "message": "Welcome to Wayfarer API",
        "environment": "development",
        "version": "0.1.0",
    }