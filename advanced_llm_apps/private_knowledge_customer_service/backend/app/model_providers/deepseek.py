"""DeepSeek adapter reusing the repository's OpenAI-compatible pattern."""

from typing import Any, Callable

from app.model_providers.base import ModelLocation, ModelRequest


class DeepSeekProvider:
    name = "deepseek"
    location = ModelLocation.CLOUD

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "deepseek-v4-flash",
        client_factory: Callable[..., Any] | None = None,
    ) -> None:
        if not api_key.strip():
            raise ValueError("DeepSeek API 密钥不能为空")
        if client_factory is None:
            from openai import OpenAI

            client_factory = OpenAI
        # Same OpenAI-compatible endpoint used by ai_system_architect_r1.
        self._client = client_factory(
            api_key=api_key,
            base_url="https://api.deepseek.com",
        )
        self.model = model

    def generate(self, request: ModelRequest) -> str:
        response = self._client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": request.system},
                {"role": "user", "content": request.user},
            ],
            temperature=0,
        )
        content = response.choices[0].message.content
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("DeepSeek 未返回有效答案")
        return content.strip()
