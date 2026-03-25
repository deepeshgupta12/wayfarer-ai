from abc import ABC, abstractmethod
from typing import Any


class BaseChatProvider(ABC):
    provider_name: str

    @abstractmethod
    def get_status(self) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def generate_json(self, prompt: str, schema: dict[str, Any]) -> dict[str, Any] | None:
        raise NotImplementedError