from __future__ import annotations

from typing import Any

import requests

from gwisp.adapters.llm_ollama import OllamaClient
from gwisp.config import AppSettings
from gwisp.domain.ports import LlmClient
from gwisp.services.prompts import SYSTEM_PROMPT

SUPPORTED_LLM_PROVIDERS = {"ollama", "cloud"}


def normalized_llm_provider(provider: str | None) -> str:
    normalized = (provider or "ollama").strip().lower()
    if normalized not in SUPPORTED_LLM_PROVIDERS:
        raise ValueError("llm_provider must be either 'ollama' or 'cloud'")
    return normalized


def create_llm_client(settings: AppSettings) -> LlmClient:
    provider = normalized_llm_provider(settings.llm_provider)
    if provider == "cloud":
        return CloudChatClient(settings)
    return OllamaClient(settings)


class CloudChatClient:
    provider_name = "cloud"
    display_name = "Cloud API"

    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings

    @property
    def model_name(self) -> str:
        return str(self.settings.cloud_model).strip()

    @property
    def api_url(self) -> str:
        return str(self.settings.cloud_api_url).strip()

    @property
    def timeout(self) -> tuple[float, float]:
        return (
            self.settings.cloud_connect_timeout_seconds,
            self.settings.cloud_request_timeout_seconds,
        )

    @property
    def headers(self) -> dict[str, str]:
        api_key = str(self.settings.cloud_api_key).strip()
        if not api_key:
            raise RuntimeError(
                "cloud_api_key is required for llm_provider='cloud'. "
                "Set GWISP_CLOUD_API_KEY or add cloud_api_key to your local config.json."
            )

        authorization = api_key if api_key.lower().startswith("bearer ") else f"Bearer {api_key}"
        return {
            "Authorization": authorization,
            "Content-Type": "application/json",
        }

    def build_payload(self, question: str, max_tokens: int | None = None) -> dict[str, Any]:
        token_limit = int(max_tokens if max_tokens is not None else self.settings.cloud_max_tokens)
        payload: dict[str, Any] = {
            "model": self.model_name,
            "messages": [
                {"role": "developer", "content": SYSTEM_PROMPT},
                {"role": "user", "content": question},
            ],
            "stream": False,
            "temperature": self.settings.cloud_temperature,
        }
        if token_limit > 0:
            payload["max_tokens"] = token_limit
        return payload

    def warm_up(self) -> str:
        answer = self._request("Load check. Reply exactly: READY", max_tokens=20)
        if not answer:
            raise RuntimeError("cloud model returned an empty warm-up response")
        return f"Cloud API model ready: {self.model_name}"

    def ask(self, question: str) -> str:
        answer = self._request(question)
        if not answer:
            return "(Cloud API returned an empty response.)"
        return answer

    def _request(self, question: str, max_tokens: int | None = None) -> str:
        if not self.api_url:
            raise RuntimeError("cloud_api_url is required for llm_provider='cloud'")
        if not self.model_name:
            raise RuntimeError("cloud_model is required for llm_provider='cloud'")

        response = requests.post(
            self.api_url,
            headers=self.headers,
            json=self.build_payload(question, max_tokens=max_tokens),
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        choices = data.get("choices") or []
        if not choices:
            return ""

        message = choices[0].get("message") or {}
        return _content_to_text(message.get("content")).strip()


def _content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "\n".join(parts)
    return ""
