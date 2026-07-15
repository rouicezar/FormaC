from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings


def create_session_factory() -> sessionmaker[Session]:
    settings = get_settings()
    if not settings.database_url:
        raise RuntimeError("PKCS_DATABASE_URL is required")
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    return sessionmaker(bind=engine, expire_on_commit=False)


def get_session() -> Generator[Session, None, None]:
    factory = create_session_factory()
    with factory() as session:
        yield session
