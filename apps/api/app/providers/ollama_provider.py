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