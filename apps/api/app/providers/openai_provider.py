from typing import Any

from app.core.config import get_settings
from app.providers.base import BaseChatProvider


class OpenAIChatProvider(BaseChatProvider):
    provider_name = "openai"

    def __init__(self) -> None:
        self.settings = get_settings()

    def get_status(self) -> dict[str, Any]:
        api_key_present = (
            bool(self.settings.openai_api_key)
            and self.settings.openai_api_key != "YOUR_OPENAI_API_KEY"
        )

        return {
            "provider": self.provider_name,
            "configured": api_key_present,
            "model": self.settings.openai_model,
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