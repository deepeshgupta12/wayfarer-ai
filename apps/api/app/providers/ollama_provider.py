from __future__ import annotations

import json
from typing import Any

import httpx

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
        if not self.get_status()["configured"]:
            return None

        url = f"{self.settings.ollama_base_url.rstrip('/')}/api/chat"
        grounded_prompt = (
            f"{prompt}\n\n"
            "Return JSON only. Follow this JSON schema exactly:\n"
            f"{json.dumps(schema)}"
        )
        body = {
            "model": self.settings.ollama_chat_model,
            "stream": False,
            "messages": [
                {
                    "role": "user",
                    "content": grounded_prompt,
                }
            ],
            "format": schema,
            "options": {
                "temperature": 0,
            },
        }

        try:
            with httpx.Client(timeout=self.settings.external_api_timeout_seconds) as client:
                response = client.post(url, json=body)
                response.raise_for_status()
                payload = response.json()

            message = payload.get("message", {})
            content = message.get("content")

            if not isinstance(content, str) or not content.strip():
                return None

            return json.loads(content)
        except Exception:
            return None