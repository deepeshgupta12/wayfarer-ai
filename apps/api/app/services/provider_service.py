from typing import Any

from app.core.config import get_settings
from app.providers.ollama_provider import OllamaChatProvider
from app.providers.openai_provider import OpenAIChatProvider


def get_provider_status() -> dict[str, Any]:
    settings = get_settings()

    openai_provider = OpenAIChatProvider()
    ollama_provider = OllamaChatProvider()

    return {
        "default_llm_provider": settings.default_llm_provider,
        "default_embed_provider": settings.default_embed_provider,
        "providers": {
            "openai": openai_provider.get_status(),
            "ollama": ollama_provider.get_status(),
        },
    }