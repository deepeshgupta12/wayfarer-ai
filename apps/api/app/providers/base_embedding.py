from abc import ABC, abstractmethod
from typing import Any


class BaseEmbeddingProvider(ABC):
    provider_name: str

    @abstractmethod
    def get_status(self) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def embed_text(self, text: str) -> dict[str, Any]:
        raise NotImplementedError