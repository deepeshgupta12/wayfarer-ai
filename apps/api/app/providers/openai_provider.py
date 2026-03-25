from __future__ import annotations

import json
from typing import Any

import httpx

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
        if not self.get_status()["configured"]:
            return None

        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.settings.openai_api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": self.settings.openai_model,
            "temperature": 0,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You extract structured review themes. "
                        "Return valid JSON only and strictly follow the provided schema."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "review_theme_extraction",
                    "strict": True,
                    "schema": schema,
                },
            },
        }

        try:
            with httpx.Client(timeout=self.settings.external_api_timeout_seconds) as client:
                response = client.post(url, headers=headers, json=body)
                response.raise_for_status()
                payload = response.json()

            choices = payload.get("choices", [])
            if not choices:
                return None

            message = choices[0].get("message", {})
            content = message.get("content")

            if isinstance(content, str):
                return json.loads(content)

            if isinstance(content, list):
                text_parts: list[str] = []
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        text = item.get("text")
                        if isinstance(text, str):
                            text_parts.append(text)

                if text_parts:
                    return json.loads("".join(text_parts))

            return None
        except Exception:
            return None