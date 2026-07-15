from dataclasses import dataclass
from pathlib import Path

from raglite import RAGLiteConfig
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.config import Settings
from app.customer_service.answers import AskService, ProviderRegistry
from app.domain.models import KnowledgePartition
from app.indexing.raglite_writer import RagLiteIndexWriter, RagLiteStore
from app.ingestion.service import ScanService, SqlAlchemyScanRepository
from app.model_providers.base import ModelLocation, ModelProvider, UnavailableProvider
from app.model_providers.deepseek import DeepSeekProvider
from app.model_providers.ollama import OllamaProvider
from app.retrieval.raglite_adapter import RagLiteHybridRetriever, RetrievalStore


@dataclass(slots=True)
class ApplicationRuntime:
    engine: Engine
    session: Session
    scan_service: ScanService
    ask_service: AskService

    def close(self) -> None:
        self.session.close()
        self.engine.dispose()


def build_runtime(settings: Settings) -> ApplicationRuntime:
    missing = [
        name
        for name, value in (
            ("PKCS_DATABASE_URL", settings.database_url),
            ("PKCS_KNOWLEDGE_ROOT", settings.knowledge_root),
            ("PKCS_PUBLIC_RAG_URL", settings.public_rag_url),
            ("PKCS_SENSITIVE_RAG_URL", settings.sensitive_rag_url),
        )
        if not value
    ]
    if missing:
        raise RuntimeError(f"缺少运行配置：{', '.join(missing)}")

    assert settings.database_url
    assert settings.knowledge_root
    assert settings.public_rag_url
    assert settings.sensitive_rag_url
    public_config = RAGLiteConfig(
        db_url=settings.public_rag_url,
        embedder=settings.embedding_model,
    )
    sensitive_config = RAGLiteConfig(
        db_url=settings.sensitive_rag_url,
        embedder=settings.embedding_model,
    )
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    session = Session(engine, expire_on_commit=False)
    writer = RagLiteIndexWriter(
        public_store=RagLiteStore(KnowledgePartition.PUBLIC, public_config),
        sensitive_store=RagLiteStore(KnowledgePartition.SENSITIVE, sensitive_config),
    )
    retriever = RagLiteHybridRetriever(
        public_store=RetrievalStore(KnowledgePartition.PUBLIC, public_config),
        sensitive_store=RetrievalStore(KnowledgePartition.SENSITIVE, sensitive_config),
    )
    providers: dict[str, ModelProvider] = {
        "ollama": OllamaProvider(
            model=settings.ollama_model,
            host=settings.ollama_host,
        )
    }
    if settings.deepseek_api_key:
        providers["deepseek"] = DeepSeekProvider(
            api_key=settings.deepseek_api_key,
            model=settings.deepseek_model,
        )
    else:
        providers["deepseek"] = UnavailableProvider(
            name="deepseek",
            location=ModelLocation.CLOUD,
            reason="DeepSeek API 密钥尚未配置",
        )

    return ApplicationRuntime(
        engine=engine,
        session=session,
        scan_service=ScanService(
            Path(settings.knowledge_root),
            SqlAlchemyScanRepository(session),
            writer,
        ),
        ask_service=AskService(
            retriever=retriever,
            providers=ProviderRegistry(providers),
        ),
    )
