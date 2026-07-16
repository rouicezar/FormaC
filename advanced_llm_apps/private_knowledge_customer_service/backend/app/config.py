from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    service_name: str = "private-knowledge-customer-service"
    database_url: str | None = None
    knowledge_root: str | None = None
    public_rag_url: str | None = None
    sensitive_rag_url: str | None = None
    embedding_model: str = "ollama/embeddinggemma:latest"
    deepseek_api_key: str | None = None
    deepseek_model: str = "deepseek-chat"
    ollama_model: str = "qwen3:0.6b"
    ollama_host: str = "http://localhost:11434"
    active_provider: str = "ollama"
    allow_sensitive_cloud: bool = False
    admin_config_path: str = ".data/admin-config.json"
    feishu_app_id: str | None = None
    feishu_app_secret: str | None = None

    model_config = SettingsConfigDict(
        env_prefix="PKCS_",
        env_file=".env",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
