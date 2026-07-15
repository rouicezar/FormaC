from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    service_name: str = "private-knowledge-customer-service"
    database_url: str | None = None
    knowledge_root: str | None = None
    deepseek_api_key: str | None = None
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

