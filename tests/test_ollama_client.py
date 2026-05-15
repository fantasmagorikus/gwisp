from gwisp.adapters.llm_ollama import OllamaClient
from gwisp.config import AppSettings


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
