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
from app.retrieval.search_service import OriginalSearchService
from app.permissions.identities import IdentityService, SqlAlchemyIdentityRepository
from app.channels.feishu.events import (
    FeishuChannelService,
    FeishuReplyClient,
    SqlAlchemyFeishuEventRepository,
)
from app.records import SqlAlchemyInteractionRecordRepository


@dataclass(slots=True)
class ApplicationRuntime:
    engine: Engine
    session: Session
    scan_service: ScanService
    search_service: OriginalSearchService
    ask_service: AskService
    identity_service: IdentityService
    feishu_service: FeishuChannelService
    feishu_reply_client: FeishuReplyClient | None
    records_repository: SqlAlchemyInteractionRecordRepository

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

    search_service = OriginalSearchService(retriever=retriever)
    ask_service = AskService(
        retriever=retriever,
        providers=ProviderRegistry(providers),
    )
    identity_service = IdentityService(SqlAlchemyIdentityRepository(engine))
    records_repository = SqlAlchemyInteractionRecordRepository(engine)
    return ApplicationRuntime(
        engine=engine,
        session=session,
        scan_service=ScanService(
            Path(settings.knowledge_root),
            SqlAlchemyScanRepository(engine),
            writer,
        ),
        search_service=search_service,
        ask_service=ask_service,
        identity_service=identity_service,
        feishu_service=FeishuChannelService(
            repository=SqlAlchemyFeishuEventRepository(engine),
            identities=identity_service,
            search_service=search_service,
            ask_service=ask_service,
            records_repository=records_repository,
        ),
        feishu_reply_client=(
            FeishuReplyClient(settings.feishu_app_id, settings.feishu_app_secret)
            if settings.feishu_app_id and settings.feishu_app_secret
            else None
        ),
        records_repository=records_repository,
    )
