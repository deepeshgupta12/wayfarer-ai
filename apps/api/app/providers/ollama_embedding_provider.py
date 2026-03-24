from typing import Any

from app.core.config import get_settings
from app.providers.base_embedding import BaseEmbeddingProvider


class OllamaEmbeddingProvider(BaseEmbeddingProvider):
    provider_name = "ollama"

    def __init__(self) -> None:
        self.settings = get_settings()

    def get_status(self) -> dict[str, Any]:
        base_url_present = bool(self.settings.ollama_base_url)
        model_present = bool(self.settings.ollama_embed_model)

        return {
            "provider": self.provider_name,
            "configured": base_url_present and model_present,
            "base_url": self.settings.ollama_base_url,
            "model": self.settings.ollama_embed_model,
        }

    def embed_text(self, text: str) -> dict[str, Any]:
        # Foundation stub only. Real Ollama embedding call comes later.
        return {
            "provider": self.provider_name,
            "model": self.settings.ollama_embed_model,
            "dimensions": 8,
            "vector": [
                float(len(text)),
                float(len(text.split())),
                1.1,
                1.2,
                1.3,
                1.4,
                1.5,
                1.6,
            ],
        }