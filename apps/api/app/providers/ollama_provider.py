from typing import Any

from app.core.config import get_settings
from app.providers.base import BaseChatProvider


class OllamaChatProvider(BaseChatProvider):
    provider_name = "ollama"

    def __init__(self) -> None:
        self.settings = get_settings()

    def get_status(self) -> dict[str, Any]:
        base_url_present = bool(self.settings.ollama_base_url)
        model_present = bool(self.settings.ollama_chat_model)

        return {
            "provider": self.provider_name,
            "configured": base_url_present and model_present,
            "base_url": self.settings.ollama_base_url,
            "model": self.settings.ollama_chat_model,
        }

    def generate_json(self, prompt: str, schema: dict[str, Any]) -> dict[str, Any] | None:
        _ = prompt
        _ = schema

        # Step 26 foundation:
        # provider-backed structured generation hook exists,
        # but falls back to deterministic heuristics when no live implementation is configured.
        if not self.get_status()["configured"]:
            return None

        return None