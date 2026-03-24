from tests.conftest import get_test_client


def test_provider_status_endpoint_returns_expected_structure() -> None:
    client = get_test_client()

    response = client.get("/providers/status")

    assert response.status_code == 200

    payload = response.json()

    assert payload["default_llm_provider"] == "openai"
    assert payload["default_embed_provider"] == "ollama"
    assert "providers" in payload
    assert "openai" in payload["providers"]
    assert "ollama" in payload["providers"]

    assert payload["providers"]["openai"]["provider"] == "openai"
    assert payload["providers"]["openai"]["model"] == "gpt-4o-mini"

    assert payload["providers"]["ollama"]["provider"] == "ollama"
    assert payload["providers"]["ollama"]["model"] == "llama3.1"