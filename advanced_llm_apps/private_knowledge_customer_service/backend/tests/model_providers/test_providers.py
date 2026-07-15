from types import SimpleNamespace

import pytest

from app.model_providers.base import ModelLocation, ModelRequest
from app.model_providers.deepseek import DeepSeekProvider
from app.model_providers.ollama import OllamaProvider


def test_deepseek_reuses_openai_compatible_endpoint() -> None:
    captured: dict = {}

    class Completions:
        def create(self, **kwargs):
            captured["request"] = kwargs
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content=" 云端答案 "))]
            )

    def factory(**kwargs):
        captured["client"] = kwargs
        return SimpleNamespace(chat=SimpleNamespace(completions=Completions()))

    provider = DeepSeekProvider(api_key="secret", client_factory=factory)
    answer = provider.generate(ModelRequest(system="规则", user="问题"))

    assert provider.location is ModelLocation.CLOUD
    assert captured["client"] == {
        "api_key": "secret",
        "base_url": "https://api.deepseek.com",
    }
    assert captured["request"]["model"] == "deepseek-chat"
    assert answer == "云端答案"


def test_deepseek_rejects_empty_key() -> None:
    with pytest.raises(ValueError, match="密钥"):
        DeepSeekProvider(api_key=" ", client_factory=lambda **_: object())


def test_ollama_reuses_agno_model() -> None:
    captured: dict = {}

    class Model:
        def response(self, messages):
            captured["messages"] = messages
            return SimpleNamespace(content=" 本地答案 ")

    def model_factory(**kwargs):
        captured["model"] = kwargs
        return Model()

    def message_factory(**kwargs):
        return kwargs

    provider = OllamaProvider(
        model="qwen3:latest",
        host="http://localhost:11434",
        model_factory=model_factory,
        message_factory=message_factory,
    )
    answer = provider.generate(ModelRequest(system="规则", user="问题"))

    assert provider.location is ModelLocation.LOCAL
    assert captured["model"] == {
        "id": "qwen3:latest",
        "host": "http://localhost:11434",
    }
    assert captured["messages"][1]["content"] == "问题"
    assert answer == "本地答案"
