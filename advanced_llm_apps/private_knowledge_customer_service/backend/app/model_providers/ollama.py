"""Ollama adapter reusing the repository's Agno Ollama model pattern."""

from typing import Any, Callable

from app.model_providers.base import ModelLocation, ModelRequest


class OllamaProvider:
    name = "ollama"
    location = ModelLocation.LOCAL

    def __init__(
        self,
        *,
        model: str = "qwen3:0.6b",
        host: str | None = None,
        model_factory: Callable[..., Any] | None = None,
        message_factory: Callable[..., Any] | None = None,
    ) -> None:
        if model_factory is None or message_factory is None:
            from agno.models.message import Message
            from agno.models.ollama import Ollama

            model_factory = model_factory or Ollama
            message_factory = message_factory or Message
        kwargs: dict[str, Any] = {"id": model}
        if host:
            kwargs["host"] = host
        self._model = model_factory(**kwargs)
        self._message_factory = message_factory
        self.model = model

    def generate(self, request: ModelRequest) -> str:
        response = self._model.response(
            [
                self._message_factory(role="system", content=request.system),
                self._message_factory(role="user", content=request.user),
            ]
        )
        content = response.content
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("Ollama 未返回有效答案")
        return content.strip()
