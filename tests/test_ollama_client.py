import pytest

from gwisp.adapters.llm_clients import CloudChatClient, create_llm_client
from gwisp.adapters.llm_ollama import OllamaClient
from gwisp.config import AppSettings, load_settings


def test_build_payload_uses_settings_and_disables_streaming() -> None:
    settings = AppSettings(
        ollama_model="local-model",
        ollama_num_gpu=12,
        ollama_num_ctx=1024,
        ollama_num_predict=77,
        ollama_temperature=0.2,
        ollama_keep_alive="10m",
    )
    client = OllamaClient(settings)

    payload = client.build_payload("Question?")

    assert payload["model"] == "local-model"
    assert payload["prompt"] == "Question?"
    assert payload["stream"] is False
    assert payload["think"] is False
    assert payload["keep_alive"] == "10m"
    assert payload["options"] == {
        "num_gpu": 12,
        "num_ctx": 1024,
        "num_predict": 77,
        "temperature": 0.2,
    }


def test_tags_url_is_derived_from_generate_url() -> None:
    settings = AppSettings(ollama_url="http://localhost:11434/api/generate")
    client = OllamaClient(settings)

    assert client.tags_url == "http://localhost:11434/api/tags"


def test_create_llm_client_uses_local_ollama_by_default() -> None:
    client = create_llm_client(AppSettings())

    assert isinstance(client, OllamaClient)
    assert client.display_name == "Local Ollama"


def test_create_llm_client_uses_cloud_chat_when_configured() -> None:
    settings = AppSettings(llm_provider="cloud", cloud_api_key="sk-test")

    client = create_llm_client(settings)

    assert isinstance(client, CloudChatClient)
    assert client.display_name == "Cloud API"


def test_cloud_chat_payload_uses_chat_completion_shape() -> None:
    settings = AppSettings(
        llm_provider="cloud",
        cloud_api_url="https://example.test/v1/chat/completions",
        cloud_api_key="sk-test",
        cloud_model="cloud-model",
        cloud_max_tokens=77,
        cloud_temperature=0.2,
    )
    client = CloudChatClient(settings)

    payload = client.build_payload("Question?")

    assert payload["model"] == "cloud-model"
    assert payload["stream"] is False
    assert payload["max_tokens"] == 77
    assert payload["temperature"] == 0.2
    assert payload["messages"][0]["role"] == "developer"
    assert payload["messages"][1] == {"role": "user", "content": "Question?"}
    assert client.headers["Authorization"] == "Bearer sk-test"


def test_cloud_chat_requires_api_key_before_network_call() -> None:
    client = CloudChatClient(AppSettings(llm_provider="cloud", cloud_api_key=""))

    with pytest.raises(RuntimeError, match="cloud_api_key"):
        client.ask("Question?")


def test_cloud_chat_ask_extracts_first_message_content(monkeypatch) -> None:
    settings = AppSettings(
        llm_provider="cloud",
        cloud_api_url="https://example.test/v1/chat/completions",
        cloud_api_key="sk-test",
        cloud_model="cloud-model",
    )
    client = CloudChatClient(settings)
    calls = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"choices": [{"message": {"content": "Answer: B"}}]}

    def fake_post(url, *, headers, json, timeout):
        calls["url"] = url
        calls["headers"] = headers
        calls["json"] = json
        calls["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr("gwisp.adapters.llm_clients.requests.post", fake_post)

    answer = client.ask("Question?")

    assert answer == "Answer: B"
    assert calls["url"] == "https://example.test/v1/chat/completions"
    assert calls["headers"]["Authorization"] == "Bearer sk-test"
    assert calls["json"]["messages"][1]["content"] == "Question?"


def test_load_settings_accepts_cloud_api_key_from_environment(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("GWISP_CLOUD_API_KEY", "sk-env")
    settings = load_settings(tmp_path / "config.json")

    assert settings.cloud_api_key == "sk-env"
