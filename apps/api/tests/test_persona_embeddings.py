from tests.conftest import get_test_client


def test_generate_and_save_persona_embedding_returns_expected_structure() -> None:
    client = get_test_client()

    persona_response = client.post(
        "/persona/initialize-and-save",
        json={
            "traveller_id": "traveller_embed_001",
            "travel_style": "midrange",
            "pace_preference": "balanced",
            "group_type": "couple",
            "interests": ["food", "culture"],
        },
    )
    assert persona_response.status_code == 200

    response = client.post(
        "/persona-embeddings/generate-and-save",
        json={
            "traveller_id": "traveller_embed_001",
        },
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["provider"] == "ollama"
    assert payload["model"] == "nomic-embed-text"
    assert payload["dimensions"] == 8
    assert isinstance(payload["vector"], list)
    assert len(payload["vector"]) == 8