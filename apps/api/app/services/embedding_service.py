from app.core.config import get_settings
from app.providers.ollama_embedding_provider import OllamaEmbeddingProvider
from app.providers.openai_embedding_provider import OpenAIEmbeddingProvider
from app.schemas.embedding import EmbeddingResponse

settings = get_settings()


def _resolve_provider(provider_override: str | None):
    provider_name = provider_override or settings.default_embed_provider

    if provider_name == "openai":
        return OpenAIEmbeddingProvider()

    return OllamaEmbeddingProvider()


def get_embedding(text: str, provider_override: str | None = None) -> EmbeddingResponse:
    provider = _resolve_provider(provider_override)
    result = provider.embed_text(text)

    return EmbeddingResponse(**result)


def get_embedding_provider_status() -> dict[str, object]:
    openai_provider = OpenAIEmbeddingProvider()
    ollama_provider = OllamaEmbeddingProvider()

    return {
        "default_embed_provider": settings.default_embed_provider,
        "providers": {
            "openai": openai_provider.get_status(),
            "ollama": ollama_provider.get_status(),
        },
    }