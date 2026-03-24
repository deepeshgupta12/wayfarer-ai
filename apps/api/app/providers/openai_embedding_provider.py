from typing import Any

from app.core.config import get_settings
from app.providers.base_embedding import BaseEmbeddingProvider


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
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
            "model": "text-embedding-3-small",
        }

    def embed_text(self, text: str) -> dict[str, Any]:
        # Foundation stub only. Real API call comes later.
        return {
            "provider": self.provider_name,
            "model": "text-embedding-3-small",
            "dimensions": 8,
            "vector": [
                float(len(text)),
                float(len(text.split())),
                0.1,
                0.2,
                0.3,
                0.4,
                0.5,
                0.6,
            ],
        }