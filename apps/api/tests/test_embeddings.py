from tests.conftest import get_test_client


def test_embedding_status_endpoint_returns_expected_structure() -> None:
    client = get_test_client()

    response = client.get("/embeddings/status")

    assert response.status_code == 200

    payload = response.json()

    assert payload["default_embed_provider"] == "ollama"
    assert "providers" in payload
    assert "openai" in payload["providers"]
    assert "ollama" in payload["providers"]


def test_generate_embedding_returns_expected_structure() -> None:
    client = get_test_client()

    response = client.post(
        "/embeddings/generate",
        json={
            "text": "Kyoto is perfect for food and culture lovers.",
        },
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["provider"] == "ollama"
    assert payload["model"] == "nomic-embed-text"
    assert payload["dimensions"] == 8
    assert isinstance(payload["vector"], list)
    assert len(payload["vector"]) == 8