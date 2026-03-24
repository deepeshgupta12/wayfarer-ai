from abc import ABC, abstractmethod
from typing import Any


class BaseChatProvider(ABC):
    provider_name: str

    @abstractmethod
    def get_status(self) -> dict[str, Any]:
        raise NotImplementedError