from pathlib import Path

import pytest

from app.config import Settings
from app.runtime import build_runtime


def test_runtime_requires_all_local_knowledge_storage_settings() -> None:
    with pytest.raises(RuntimeError, match="PKCS_DATABASE_URL.*PKCS_KNOWLEDGE_ROOT"):
        build_runtime(
            Settings(
                database_url=None,
                knowledge_root=None,
                public_rag_url=None,
                sensitive_rag_url=None,
            )
        )


def test_runtime_assembles_reused_providers_without_connecting(tmp_path: Path) -> None:
    root = tmp_path / "knowledge"
    (root / "public").mkdir(parents=True)
    (root / "sensitive").mkdir()
    settings = Settings(
        database_url="postgresql+psycopg://user:pass@localhost/main",
        knowledge_root=str(root),
        public_rag_url="postgresql+psycopg://user:pass@localhost/public",
        sensitive_rag_url="postgresql+psycopg://user:pass@localhost/sensitive",
        ollama_model="qwen3:latest",
    )

    runtime = build_runtime(settings)
    try:
        assert runtime.scan_service.knowledge_root == root
        assert runtime.search_service.retriever is runtime.ask_service.retriever
        assert runtime.ask_service.providers.get("ollama").model == "qwen3:latest"
        deepseek = runtime.ask_service.providers.get("deepseek")
        with pytest.raises(ValueError, match="密钥尚未配置"):
            deepseek.generate(None)  # type: ignore[arg-type]
    finally:
        runtime.close()
