import re

import requests

from gwisp.config import AppSettings
from gwisp.services.prompts import SYSTEM_PROMPT


class OllamaClient:
    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings

    @property
    def tags_url(self) -> str:
        generate_url = str(self.settings.ollama_url).strip().rstrip("/")
        base_url = re.sub(r"/api/.*$", "", generate_url)
        return f"{base_url}/api/tags"

    @property
    def timeout(self) -> tuple[float, float]:
        return (
            self.settings.ollama_connect_timeout_seconds,
            self.settings.ollama_request_timeout_seconds,
        )

    def installed_models(self) -> set[str]:
        response = requests.get(self.tags_url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()
        return {
            str(model.get("name") or model.get("model") or "") for model in data.get("models", [])
        }

    def check_model_available(self) -> None:
        model_name = str(self.settings.ollama_model)
        available = self.installed_models()

        if model_name not in available:
            available_text = ", ".join(sorted(available)) or "(none)"
            raise RuntimeError(
                f"model '{model_name}' not found in Ollama. Run: ollama pull {model_name}. "
                f"Available models: {available_text}"
            )

    def build_payload(self, question: str, num_predict: int | None = None) -> dict:
        payload = {
            "model": str(self.settings.ollama_model),
            "system": SYSTEM_PROMPT,
            "prompt": question,
            "stream": False,
            "think": False,
            "options": {
                "num_gpu": self.settings.ollama_num_gpu,
                "num_ctx": self.settings.ollama_num_ctx,
                "num_predict": int(num_predict or self.settings.ollama_num_predict),
                "temperature": self.settings.ollama_temperature,
            },
        }

        keep_alive = str(self.settings.ollama_keep_alive).strip()
        if keep_alive:
            payload["keep_alive"] = keep_alive

        return payload

    def warm_up(self) -> str:
        self.check_model_available()
        payload = self.build_payload("Load check. Reply exactly: READY", num_predict=20)
        response = requests.post(
            str(self.settings.ollama_url),
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        answer = str(data.get("response", "")).strip()
        done_reason = str(data.get("done_reason", "unknown"))

        if not answer:
            raise RuntimeError(
                f"model returned an empty warm-up response; done_reason={done_reason}"
            )

        return f"model loaded and ready: {self.settings.ollama_model}"

    def ask(self, question: str) -> str:
        payload = self.build_payload(question)
        response = requests.post(
            str(self.settings.ollama_url),
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        answer = str(data.get("response", "")).strip()
        done_reason = str(data.get("done_reason", "unknown"))
        if not answer:
            return f"(Ollama returned an empty response. done_reason={done_reason}.)"
        return answer
